#!/usr/bin/env python3
"""
Actions for turning data into delayed specs,
for then queuing

For Example, with state(blah=['a','b','c']):
{do='job.expand', from_='blah', template='simple::task', inject={literal=['val']}, update_='specs'}
Or:
{do='job.match', from_='blah', mapping={...}, inject={literal=['val']}, update_='specs'}
then:
{do="job.queue", from_="specs"}

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
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.locator import Location
from jgdv.structs.strang import CodeReference
import doot
import doot.errors
from doot.util.factory import DelayedSpec, TaskFactory
from doot.workflow import InjectSpec, TaskName, TaskSpec
from doot.workflow._interface import Action_p, InjectSpec_i, TaskName_p, TaskSpec_i
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.workflow.actions import DootBaseAction

# ##-- end 3rd party imports

# ##-- types
# isort: off
from typing import override
if TYPE_CHECKING:
   from jgdv import Maybe
   from doot.workflow._interface import ActionSpec_i, Task_p

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

FALLBACK_KEY      : Final[str] = "_"
FALLBACK_MISSING  : Final[str] = f"Data->Source Mapping lacks a fallback value '{FALLBACK_KEY}'"
MAPPING_TYPE_FAIL : Final[str] = "Mapping is not a dict"
factory = TaskFactory()

@Proto(Action_p)
class JobExpandAction(DootBaseAction):
    """
    Expand data into a number of delayed specs.
    Does *not* queue the tasks, thats for job.queue

    `from`      : source data to inject
    `inject`    : how to map the data as literals
    `template`  : taskname of the base spec to use

    registered as: job.expand
    TODO change job subtask naming scheme
    """

    @DKeyed.taskname
    @DKeyed.formats("prefix", check=str)
    @DKeyed.types("template", check=str)
    @DKeyed.types("from", check=int|list|str|pl.Path)
    @DKeyed.types("inject", check=dict|ChainGuard)
    @DKeyed.types("__expansion_count", fallback=0)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _basename, prefix, template, _from, inject, _count, _update) -> Maybe[dict]:  # noqa: ARG002
        result       : list[DelayedSpec]
        inject_spec  : Maybe[InjectSpec_i]
        base_head    : TaskName_p
        build_queue  : list
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
            _count  += 1
            delayed  = self._delay_spec(target=base_subtask.push(prefix, _count),
                                        literal=arg,
                                        template=template,
                                        inject=inject_spec,
                                        state=state,
                                        overrides={"required_for"  : [base_head]},
                                        )
            result.append(delayed)
        else:
            return { _update : result , "__expansion_count":  _count }

    def _prep_data(self, data:Maybe[int|str|pl.Path|list]) -> list:
        """ ensure the data for subtasks is correct """
        result : list = []
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

    def _delay_spec(self, *, target:TaskName_p, template:TaskName_p, literal:Any, inject:Maybe[InjectSpec_i], state:dict, overrides:dict) -> DelayedSpec:  # noqa: PLR0913
        applied : Maybe[dict]
        match inject:
            case InjectSpec_i():
                applied = (inject.apply_from_state(state) | inject.apply_literal(literal))
            case _:
                applied = None

        delayed = factory.delay(base=template,
                                target=target,
                                inject=inject,
                                applied=applied,
                                overrides=overrides,
                                )
        return delayed

@Proto(Action_p)
class MatchExpansionAction(JobExpandAction):
    """ Create subtasks, but with context specific mapping

    Take a mapping of {pattern -> task} and a list of data,
    and build a list of delayed specs

    use `prepfn` to get a value from a taskspec to match on.

    > prepfn :: λ(spec) -> Maybe[str|TaskName]

    defaults to getting JobMatchAction._default_prep_fn,
    which tries spec.fpath for a suffix

    registered as: job.match
    """

    @override
    @DKeyed.taskname
    @DKeyed.references("prepfn")
    @DKeyed.types("mapping")
    @DKeyed.types("from", check=int|list|str|pl.Path)
    @DKeyed.types("inject", check=dict|ChainGuard)
    @DKeyed.types("__expansion_count", fallback=0)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _basename, prepfn, mapping, _from, inject, _count, _update) -> Maybe[dict]:
        fn      : Callable
        result  : list[DelayedSpec]  = []
        data                         = self._prep_data(_from)
        inject_spec                  = InjectSpec.build(inject)
        base_head                    = _basename.with_head()
        if not bool(_from):
            return None

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
        for val in data:
            _count += 1
            match fn(val):
                case x if x in mapping:
                    template = mapping[x]
                case TaskName() as x:
                    template = x
                case _:
                    template = mapping[FALLBACK_KEY]
            ##--|
            target_name  = TaskName(template).push("matched", _count)
            delayed      = self._delay_spec(template=template,
                                            target=target_name,
                                            literal=val,
                                            inject=inject_spec,
                                            state=state,
                                            ##
                                            overrides={"required_for" : [base_head]})
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


@Proto(Action_p)
class JobQueueAction:
    """
      An action that returns a list of tasks to queue, instead of a dict,
    which signals the doot backend to queue the items of the list


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
    @DKeyed.taskname
    def __call__(self, spec, state, _args, _from, _basename) -> Maybe[list]:
        result  : list[TaskName_p|TaskSpec_i|DelayedSpec]
        match _from(spec, state), _args:
            case DKey() | [], []: # Nothing to do
                return None
            case DKey(), [*xs]: # simple args provided
                assert(all(isinstance(x, str) for x in xs))
                return [TaskName(x) for x in xs]
            case [*xs], [*ys]:
                result = [*xs]
                result += [TaskName(y) for y in ys]

        assert(all(isinstance(x, TaskName_p|DelayedSpec|TaskSpec_i) for x in result))
        return result
