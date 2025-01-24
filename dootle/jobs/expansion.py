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
import doot
import doot.errors
from doot.actions.base_action import DootBaseAction
from doot.enums import ActionResponse_e as ActRE
from doot.structs import DKeyed, Location, TaskName, TaskSpec
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.jobs.injection import JobInjector

# ##-- end 1st party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe
   from doot.structs import ActionSpec

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class JobExpandAction(JobInjector):
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
    @DKeyed.types("inject", check=dict)
    @DKeyed.types("__expansion_count", fallback=0)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _basename, prefix, template, _from, inject, _count, _update):
        actions, sources = self._prep_template(template)
        build_queue      = self._prep_data(_from)

        match prefix:
            case "prefix":
                prefix = "{JobGenerated}"
            case _:
                pass

        result          = []
        root            = _basename.pop()
        base_head       = root.with_head()
        match sources:
            case [] | [None]:
                base_subtask = root
            case [*xs, x]:
                base_subtask = x

        for arg in build_queue:
            _count += 1
            # TODO change job subtask naming scheme
            base_dict = dict(name=base_subtask.push(prefix, _count), # noqa: C408
                             sources=sources,
                             actions = actions or [],
                             required_for=[base_head],
                             )
            match self.build_injection(spec, state, inject, replacement=arg):
                case None:
                    pass
                case dict() as val:
                    base_dict.update(val)

            new_spec  = TaskSpec.build(base_dict)
            result.append(new_spec)
        else:
            return { _update : result , "__expansion_count":  _count }

    def _prep_data(self, data:list) -> list:
        result = []
        match data:
            case int():
                result += range(_from)
            case str() | pl.Path() | Location():
                result.append(_from)
            case []:
                pass
            case list():
                result += _from
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

class JobMatchAction(DootBaseAction):
    """
      Take a mapping of {pattern -> task} and a list,
      and build a list of new subtasks

      use `prepfn` to get a value from a taskspec to match on.

      defaults to getting spec.extra.fpath.suffix

    registered as: job.match
    """

    @DKeyed.redirects("onto_")
    @DKeyed.references("prepfn")
    @DKeyed.types("mapping")
    def __call__(self, spec, state, _onto, prepfn, mapping):
        match prepfn:
            case CodeReference():
                fn = prepfn()
            case None:

                def fn(x) -> str:
                    return x.extra.fpath.suffix

        _onto_val = _onto.expands(spec, state)
        for x in _onto_val:
            match fn(x):
                case str() as key if key in mapping:
                    x.ctor = TaskName(mapping[key])
                case _:
                    pass
