#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import typing
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
from doot.structs import TaskName, TaskSpec
from doot._abstract.task import Action_p
from jgdv.structs.dkey import DKeyed, DKey

# ##-- end 3rd party imports

# ##-- type aliases
# isort: off
if typing.TYPE_CHECKING:
   from jgdv import Maybe

# isort: on
# ##-- end type aliases

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class JobQueueAction(Action_p):
    """
      Queues a list of tasks/specs into the tracker.

      1) Queue Named Tasks: {do='job.queue', args=['group::task'] }
      2) Queue Expanded TaskSpecs: {do='job.queue', from_='state_key' }

      tasks can be specified by name in `args`
      and from prior expansion state vars with `from_` (accepts a list)

      `after` can be used to specify additional `depends_on` entries.
      (the job head is specified using `$head$`)

    registered as: job.queue
    """

    @DKeyed.args
    @DKeyed.redirects("from_", multi=True)
    @DKeyed.types("after", check=list|TaskName|str|None, fallback=None)
    @DKeyed.taskname
    def __call__(self, spec, state, _args, _from, _after, _basename) -> list:
        subtasks               = []
        queue : list[TaskSpec] = []
        _after                     = self._expand_afters(_after, _basename)

        if _args:
            queue += self._build_args(_basename, _args)

        if _from:
            queue += self._build_from_list(_basename, _from, spec,state)

        for sub in queue:
            match sub:
                case TaskSpec():
                    sub.depends_on += _after
                    subtasks.append(sub)
                case x:
                    raise doot.errors.ActionError("Tried to queue a not TaskSpec", x)

        return subtasks

    def _expand_afters(self, afters:list|str|None, base:TaskName) -> list[TaskName]:
        result = []
        match afters:
            case str():
                afters = [afters]
            case None:
                afters = []

        for x in afters:
            if x == "$head$":
                result.append(base.head_task())
            else:
                result.append(TaskName(x))

        return result

    def _build_args(self, base, args) -> list:
        result = []
        root   = base.pop()
        head   = base.with_head()
        for i,x in enumerate(args):
            sub = TaskSpec.build(dict(
                name=root.push(i),
                sources=[TaskName(x)],
                required_for=[head],
                depends_on=[],
                ))
            result.append(sub)

        return result

    def _build_from_list(self, base:TaskName, froms:list[DKey], spec, state) -> list:
        result  = []
        root    = base.pop()
        head    = base.with_head()
        assert(all(isinstance(x, DKey) for x in froms))

        for key in froms:
            if key == "from_":
                continue
            match key.expand(spec, state):
                case None:
                    pass
                case list() as l:
                    result += l
                case TaskSpec() as s:
                    result.append(s)

        return result

    def _build_from(self, base, _from:list) -> list:
        result = []
        head = base.with_head()()
        match _from:
            case None:
                pass
            case list() as l:
                result += l

        return result
