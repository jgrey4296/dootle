#!/usr/bin/env python3
"""
An FSM b acked Task and job
"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from jgdv import Proto, Mixin, Maybe
import doot
from doot.workflow import TaskSpec, ActionSpec, RelationSpec, TaskName, DootTask
from doot.workflow._interface import Task_i, Job_p, TaskMeta_e, TaskStatus_e, Task_p
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.control.tracker._interface import TaskTracker_p
from . import _interface as API

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
from types import LambdaType

if TYPE_CHECKING:
    from jgdv import Maybe, Lambda
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
skip_msg           : Final[str]  = doot.constants.printer.skip_by_condition_msg
STATE_TASK_NAME_K  : Final[str]  = doot.constants.patterns.STATE_TASK_NAME_K # type: ignore

SETUP_GROUP        : Final[str]  = "setup"
ACTION_GROUP       : Final[str]  = "actions"
FAIL_GROUP         : Final[str]  = "on_fail"
DEPENDS_GROUP      : Final[str]  = "depends_on"

# Body:

class _Predicates_m:

    ##--| setup

    def spec_missing(self, *, tracker:TaskTracker_p) -> bool:
        """ cancels the task if the spec is not registered """
        if self.spec is None or self.spec not in tracker._registry.specs:
            return True
        return False

    def should_disable(self) -> bool:
        """ cancels the task if the spec is disabled """
        return self.spec.extra.on_fail(False).disabled()

    ##--| prepare

    def should_cancel(self) -> bool:
        """ Cancel if you've waited too long """
        return self.priority < 1

    def should_wait(self, *, tracker:TaskTracker_p) -> bool:
        """ if any dependencies have not run, delay this task  """

        match tracker._network.incomplete_dependencies(self.spec.name):
            case []:
                return False
            case [*xs]:
                for x in xs:
                    tracker.queue_entry(x)
                self.priority -= 1
                return True
            case x:
                raise TypeError(type(x))

    ##--| run

    def should_skip(self) -> bool:
        """ run a task's depends_on group, coercing to a bool
        returns False if the runner should skip the rest of the task
        """
        match self._execute_action_group(group=DEPENDS_GROUP):
            case _, ActRE.SKIP | ActRE.FAIL:
                return True
            case _:
                return False

    def should_halt(self) -> bool:
        return False

    def should_fail(self) -> bool:
        return False

class _Callbacks_m:

    def on_enter_INIT(self, *, tracker):
        """
        initialise state,
        possibly run injections?
        """
        self.state |= dict(self.spec.extra)
        self.state[STATE_TASK_NAME_K]  = self.spec.name
        self.state['_action_step']     = 0

    def on_enter_RUNNING(self, step:int, tracker:TaskTracker_p) -> None:
        logmod.debug("-- Executing Task %s: %s", step, self.spec.name[:])
        match self._execute_action_group(group=SETUP_GROUP):
            case int() as x, ActRE() as res:
                # Can't queue extra actions from setup, so 2nd arg has to be []
                pass
            case x:
                raise TypeError(type(x))

        match self._execute_action_group(group=ACTION_GROUP):
            case int() as x, ActRE() as res:
                pass
            case x:
                raise TypeError(type(x))

    def on_exit_RUNNING(self, step:int, tracker:TaskTracker_p) -> None:
        # Report on the task's actions
        pass

    def on_enter_FAILED(self) -> None:
        match self._execute_action_group(group=FAIL_GROUP):
            case int() as x, ActRE() as res:
                pass
            case x:
                raise TypeError(type(x))

    def on_enter_HALTED(self) -> None:
        pass

    def on_enter_TEARDOWN(self, tracker:TaskTracker_p):
        # queue cleanup task
        match tracker._registry.concrete[self.spec.name.with_cleanup()]:
            case [x, *xs]:
                tracker.queue_entry(x, parent=self.spec.name)
            case x:
                raise TypeError(type(x))

##--|

@Proto(Task_i, API.TaskModel_p)
@Mixin(_Predicates_m, _Callbacks_m)
class FSMTask:
    """
    The implementation of a task, as the domain model for a TaskTrackMachine
    """
    _default_flags  : ClassVar[set] = set()
    step            : int
    spec            : TaskSpec
    status          : TaskStatus_e
    priority        : int
    records         : list[Any]
    state           : dict

    def __init__(self, spec:TaskSpec):
        self.step        = -1
        self.spec        = spec
        self.priority    = self.spec.priority
        self.status      = TaskStatus_e.NAMED
        self.state       = {}
        self.records     = []
        assert(self.priority > 0)

    @property
    def name(self) -> TaskName:
        return self.spec.name

    ##--| dunders

    def __repr__(self) -> str:
        cls              = self.__class__.__qualname__
        return f"<{cls}: {self.spec.name[:]}>"

    def __hash__(self) -> int:
        return hash(self.spec.name)

    def __eq__(self, other:object) -> bool:
        match other:
            case str() | TaskName():
                full     = self.spec.name
                readable = self.spec.name[:]
                return other == full or other == readable
            case Task_p():
                return self.spec.name == other.spec.name
            case _:
                return False

    ##--| internal

    def _execute_action_group(self, *, group:str) -> tuple[int, ActRE]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actions         : list[ActionSpec]
        group_result    : ActRE
        executed_count  : int

        ##--|
        actions         = self._get_action_group(group)
        group_result    = ActRE.SUCCESS
        executed_count  = 0

        for action in actions:
            match action:
                case ActionSpec():
                    pass
                case _: # Ignore relationspecs
                    continue

            match self._execute_action(executed_count, action, group=group):
                case True | None:
                    continue
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.line("Remaining Task Actions skipped by Action Result", char=".")
                    group_result = ActRE.SKIP
                    break
                case list():
                    logging.warning("Tried to queue tasks from a standard task")
                case x:
                    raise TypeError(type(x))

            executed_count += 1

        ##--|
        return executed_count, group_result

    def _execute_action(self, count:int, action:ActionSpec, group:Maybe[str]=None) -> ActRE|list[TaskSpec]:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        assert(callable(action))
        result                     = None
        self.state['_action_step'] = count
        match group:
            case str():
                doot.report.act(f"Action: {self.step}.{group}.{count}", action.do)
            case None:
                doot.report.act(f"Action: {self.step}.{count}", action.do)

        logging.debug("Action Executing for Task: %s", self.spec.name[:])
        logging.debug("Action State: %s.%s: args=%s kwargs=%s. state(size)=%s", self.step, count, action.args, dict(action.kwargs), len(self.state.keys()))
        match (result:=action(self.state)):
            case None | True:
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                raise doot.errors.TaskFailed("Task %s: Action Failed: %s", self.task.name[:], action.do, task=self.spec)
            case ActRE.SKIP:
                # result will be returned, and expand_job/execute_task will handle it
                doot.report.result(["Skip"])
                pass
            case dict(): # update the task's state
                self.state.update({str(k):v for k,v in result.items()})
                result = ActRE.SUCCESS
            case list() if all(isinstance(x, TaskName|TaskSpec) for x in result):
                pass
            case _:
                raise doot.errors.TaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", self.spec.name[:], action.do, result, task=self.spec)

        return result

    def _get_action_group(self, group_name:str) -> list[ActionSpec]:
        if hasattr(self, group_name):
            return getattr(self, group_name)
        if hasattr(self.spec, group_name):
            return getattr(self.spec, group_name)

        logging.warning("Unknown Groupname: %s", group_name)
        return []

    ##--| public

    def log(self, msg:str, level:int=logmod.DEBUG, prefix:Maybe[str]=None) -> None:
        pass

class FSMJob(FSMTask):
    """
    Extends an FSMTask for running a job
    """

    def on_enter_running(self, step, tracker):
        logmod.debug("-- Expanding Job %s: %s", step, self.spec.name[:])
        self._execute_action_group(group=SETUP_GROUP)
        match self._execute_action_group(group=ACTION_GROUP):
            case int() as x, ActRE() as res:
                pass
            case int() as x, [*xs]:
                # Queue xs
                pass
            case x:
                raise TypeError(type(x))


    def _execute_action_group(self, *, group:str) -> tuple[int, list[TaskSpec]]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actions : list[ActionSpec]

        ##--|
        actions = self._get_action_group(group)

        if not bool(actions):
            return 0, []

        group_result              = ActRE.SUCCESS
        to_queue : list[TaskSpec] = []
        executed_count            = 0

        for action in actions:
            match action:
                case ActionSpec():
                    pass
                case _:
                    continue

            match self._execute_action(executed_count, action, group=group):
                case True | None:
                    continue
                case list() as result:
                    to_queue += result
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.line("Remaining Task Actions skipped by Action Result", char=".")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # no break.
            return executed_count, to_queue

        return 0, []
