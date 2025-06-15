#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN001
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import random
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.structs.locator import Location
import doot
import doot.errors
from doot.workflow._interface import Action_p
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.workflow import TaskName, TaskSpec, InjectSpec
from doot.workflow.actions import DootBaseAction

# ##-- end 3rd party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   from doot.workflow import ActionSpec

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

FALLBACK_KEY      : Final[str] = "_"
FALLBACK_MISSING  : Final[str] = f"Data->Source Mapping lacks a fallback value '{FALLBACK_KEY}'"
MAPPING_TYPE_FAIL : Final[str] = "Mapping is not a dict"

@Proto(Action_p)
class JobExpandAction(DootBaseAction):
    """
    Expand data into a number of subtask specs.

    takes data `from` somewhere,
    and `inject`s data onto a `template`.

    registered as: job.expand
    """

    @DKeyed.taskname
    @DKeyed.formats("prefix", check=str)
    @DKeyed.types("template", check=str|list)
    @DKeyed.types("from", check=int|list|str|pl.Path)
    @DKeyed.types("inject", check=dict|ChainGuard)
    @DKeyed.types("__expansion_count", fallback=0)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _basename, prefix, template, _from, inject, _count, _update) -> Maybe[dict]:
        result       : list[TaskSpec]
        inject_spec  : Maybe[InjectSpec]
        base_head    : TaskName
        build_queue  : list
        target_name  : TaskName
        ##--|
        build_queue   = self._prep_data(_from)
        inject_spec   = InjectSpec.build(inject)
        base_head     = _basename.with_head()
        base_subtask  = _basename.push("subtasks")
        result        = []

        ##--| early exit
        if not bool(build_queue):
            return None
        ##--|
        logging.info("Generating %s SubTasks of: %s from %s", len(build_queue), template, _basename)
        for arg in build_queue:
            _count     += 1
            # TODO change job subtask naming scheme
            target_name = base_subtask.push(prefix, _count)
            result.append(self._build_spec(name=target_name,
                                           data=arg,
                                           template=template,
                                           base_req=base_head,
                                           inject=inject_spec,
                                           spec=spec,
                                           state=state))
        else:
            return { _update : result , "__expansion_count":  _count }

    def _prep_data(self, data:list) -> list:
        result = []
        match data:
            case int():
                result += range(data)
            case str() | pl.Path() | Location():
                result.append(data)
            case []:
                pass
            case list():
                result += data
            case None:
                pass
            case x:
                raise doot.errors.ActionError("Tried to expand an incompatible argument", x)

        return result

    def _prep_template(self, template:TaskName|list[ActionSpec]) -> tuple[list, TaskName|None]:
        """
          template can be the literal name of a task (template="group::task") to build off,
          or an indirect key to a list of actions (base_="sub_actions")

          This handles those possibilities and returns a list of actions and maybe a task name

        """
        match template:
            case list():
                assert(all(isinstance(x, dict|ChainGuard) for x in template))
                actions  = template
                sources  = [None]
            case TaskName():
                actions = []
                sources = [template]
            case str():
                actions = []
                sources = [TaskName(template)]
            case None:
                actions = []
                sources = [None]
            case _:
                raise doot.errors.ActionError("Unrecognized template type", template)

        return actions, sources

    def _build_spec(self, *, name:TaskName, data:Any, template:TaskName, base_req:TaskName, inject:InjectSpec, spec:ActionSpec, state:dict) -> TaskSpec:  # noqa: PLR0913
        actions, sources  = self._prep_template(template)
        match sources:
            case [*_, x] if x in doot.loaded_tasks:
                source_task = doot.loaded_tasks[x]
            case x:
                raise doot.errors.TrackingError("Unknown source task", x)

        base_dict = dict(name=name,
                         sources=sources,
                         actions = actions or [],
                         required_for=[base_req],
                         )
        if inject is not None:
            base_dict |= (inject.apply_from_spec(spec)
                          | inject.apply_from_state(state)
                          | inject.apply_literal(data)
                          )

        new_spec  = source_task.under(base_dict)
        return new_spec

@Proto(Action_p)
class MatchExpansionAction(JobExpandAction):
    """ Take a mapping of {pattern -> task} and a list,
    and build a list of new subtasks

    use `prepfn` to get a value from a taskspec to match on.

    > prepfn :: λ(spec) -> Maybe[str|TaskName]

    defaults to getting JobMatchAction._default_prep_fn,
    which tries spec.fpath for a suffix

    registered as: job.match
    """

    @DKeyed.taskname
    @DKeyed.references("prepfn")
    @DKeyed.types("mapping")
    @DKeyed.types("from", check=int|list|str|pl.Path)
    @DKeyed.types("inject", check=dict|ChainGuard)
    @DKeyed.types("__expansion_count", fallback=0)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _basename, prepfn, mapping, _from, inject, _count, _update) -> dict:
        result  : list[TaskSpec]  = []
        data                      = self._prep_data(_from)
        inject_spec               = InjectSpec.build(inject)
        base_head                 = _basename.with_head()
        if not isinstance(mapping, dict):
            raise doot.errors.TrackingError(MAPPING_TYPE_FAIL, type(mapping))
        if FALLBACK_KEY not in mapping:
            raise doot.errors.TrackingError(FALLBACK_MISSING)

        match prepfn:
            case CodeReference():
                fn = prepfn(raise_error=True)
            case None:
                fn = self._default_prep_fn
        ##--| Map data to base tasks
        mapped_data = {x:fn(x) for x in data}
        # Use the mapping
        for val in data:
            _count += 1
            template     = mapping.get(fn(val), None) or mapping[FALLBACK_KEY]
            target_name  = TaskName(template).push("matched", _count)
            result.append(self._build_spec(name=target_name,
                                           data=val,
                                           template=template,
                                           base_req=base_head,
                                           inject=inject_spec,
                                           spec=spec,
                                           state=state))
        else:
            return { _update : result , "__expansion_count":  _count }

    def _default_prep_fn(self, x:pl.Path|str) -> Maybe[str]:
        """ The default matcher. get the 'fpath' from a spec """
        match x:
            case str() as x:
                return pl.Path(x).suffix
            case pl.Path() as x:
                return x.suffix
            case _:
                return None
