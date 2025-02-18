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
from jgdv import Proto
import doot
import doot.errors
from doot.structs import TaskName, TaskSpec
from doot._abstract.task import Action_p
from jgdv.structs.dkey import DKey, DKeyed

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

@Proto(Action_p)
class JobQueueAction:
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
    @DKeyed.redirects("from_", fallback=None)
    @DKeyed.types("after", check=list|TaskName|str|None, fallback=None)
    @DKeyed.taskname
    def __call__(self, spec, state, _args, _from, _after, _basename) -> list:
        subtasks               = []
        queue : list[TaskSpec] = []
        sub_deps               = self._expand_deps(_after, _basename)

        queue += self._build_from_keys(_basename, _args, spec, state)
        queue += self._build_from_keys(_basename, _from, spec, state)

        # Now fixup the dependencies
        for sub in queue:
            match sub:
                case TaskSpec() if bool(sub_deps):
                    sub.depends_on += sub_deps
                    subtasks.append(sub)
                case TaskSpec():
                    subtasks.append(sub)
                case x:
                    raise doot.errors.ActionError("Tried to queue a not TaskSpec", x)

        return subtasks

    def _expand_deps(self, afters:list|str|None, base:TaskName) -> list[TaskName]:
        """ expand keys into dependencies """
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


    def _build_from_keys(self, base:TaskName, froms:Maybe[list[DKey|str]], spec, state) -> list:
        """ Build specs from a specified list of keys to be expanded"""
        result  = []
        root    = base.pop()
        head    = root.with_head()

        count    = 0
        match froms:
            case None:
                subtasks = []
            case [*xs]:
                subtasks = xs
            case x:
                subtasks = [x]
        while bool(subtasks):
            match subtasks.pop():
                case "from_" | None:
                    continue
                case TaskSpec() as spec:
                    result.append(spec)
                case DKey() as key:
                    match key.expand(spec, state):
                        case list() as l:
                            subtasks += l
                        case x:
                            result.append(x)
                case str() as x:
                    sub = TaskSpec.build(dict(
                        name=TaskName(x).push(count),
                        sources=[TaskName(x)],
                        required_for=[head],
                        depends_on=[],
                    ))
                    count += 1
                    subtasks.append(sub)

                case x:
                    raise doot.errors.TaskError("Unknown Type tried to be queued", x)
        else:
            return result
