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
import doot
import doot.errors
from doot._abstract import Action_p
from doot.actions.core.action import DootBaseAction
from doot.enums import ActionResponse_e as ActRE
from doot.structs import Location, TaskName, TaskSpec, InjectSpec

# ##-- end 3rd party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   from doot.structs import ActionSpec

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

FALLBACK_KEY : Final[str] = "_"

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
    def __call__(self, spec, state, _basename, prefix, template, _from, inject, _count, _update):
        actions, sources = self._prep_template(template)
        build_queue      = self._prep_data(_from)
        root            = _basename.pop()
        base_head       = root.with_head()

        match prefix:
            case "prefix":
                prefix = "{JobGenerated}"
            case _:
                pass

        match sources:
            case [] | [None]:
                base_subtask = root
            case [*xs, x]:
                base_subtask = x

        result : list[TaskSpec] = []
        logging.info("Generating %s SubTasks of: %s from %s", len(build_queue), base_subtask, root)
        for arg in build_queue:
            _count += 1
            # TODO change job subtask naming scheme
            base_dict = dict(name=base_subtask.push(prefix, _count), # noqa: C408
                             sources=sources,
                             actions = actions or [],
                             required_for=[base_head],
                             )

            match InjectSpec.build(inject, sources=[spec, state], insertion=arg):
                case None:
                    pass
                case x:
                    base_dict |= x.as_dict()

            new_spec  = TaskSpec.build(base_dict)
            result.append(new_spec)
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

@Proto(Action_p)
class JobMatchAction(DootBaseAction):
    """ Take a 'mapping' of {pattern -> task} and a list,
    and build a list of new subtasks

    use `prepfn` to get a value from a taskspec to match on.

    > prepfn :: λ(spec) -> Maybe[str|TaskName]

    defaults to getting JobMatchAction._default_suffix_matcher,
    which tries spec.fpath for a suffix

    registered as: job.match
    """

    @DKeyed.redirects("onto_")
    @DKeyed.references("prepfn")
    @DKeyed.types("mapping")
    def __call__(self, spec, state, _onto, prepfn, mapping):
        match prepfn:
            case CodeReference():
                fn = prepfn(raise_error=True)
            case None:
                fn = self._default_suffix_matcher

        _onto_val = _onto.expand(spec, state) or []
        for x in _onto_val:
            match fn(x):
                case TaskName() as target:
                    x.sources = [target]
                case None if FALLBACK_KEY in mapping:
                    x.sources = [mapping["_"]]
                case str() as key if key in mapping:
                    x.sources = [TaskName(mapping[key])]
                case _:
                    pass

    def _default_suffix_matcher(self, x:TaskSpec) -> Maybe[str]:
        match x.extra.on_fail(None).fpath():
            case None:
                return None
            case str() as x:
                return pl.Path(x).suffix
            case pl.Path() as x:
                return x.suffix
            case _:
                return None
