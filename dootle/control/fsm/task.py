#!/usr/bin/env python3
"""
An FSM b acked Task and job
"""
# ruff: noqa:
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import ChainMap
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
from doot.workflow import (ActionSpec, DootTask, InjectSpec, RelationSpec,
                           TaskName, TaskSpec)
from doot.workflow._interface import MUST_INJECT_K, CLI_K
from doot.workflow._interface import ActionResponse_e as ActRE
from doot.workflow._interface import (Job_p, Task_i, Task_p, TaskMeta_e,
                                      TaskStatus_e, TaskName_p, TaskSpec_i,
                                      DelayedSpec)
from doot.workflow.task import _TaskActionPrep_m
from jgdv import Maybe, Mixin, Proto

# ##-- end 3rd party imports

from doot.control.tracker import _interface as TrAPI # noqa: N812
from . import _interface as API  # noqa: N812
from .errors import FSMHalt, FSMSkip

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
    from doot.control.tracker._interface import WorkflowTracker_p
    from jgdv import Maybe, Lambda
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from statemachine import State

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
skip_msg           : Final[str]  = doot.constants.printer.skip_by_condition_msg
STATE_TASK_NAME_K  : Final[str]  = doot.constants.patterns.STATE_TASK_NAME_K
ACTION_STEP_K      : Final[str]  = "_action_step"
# Body:

class _Predicates_m:
    spec      : TaskSpec
    name      : TaskName_p
    priority  : int

    ##--| setup

    def spec_missing(self, *, tracker:WorkflowTracker_p) -> bool:
        """ cancels the task if the spec is not registered """
        if self.spec is None or self.spec not in tracker.specs:
            return True
        return False

    def should_disable(self, source:State, *, tracker:WorkflowTracker_p) -> bool:
        """ cancels the task if the spec is disabled """
        spec_disabled : bool = self.spec.extra.on_fail(False).disabled()  # noqa: FBT003
        match source.value:
            case TaskStatus_e.DECLARED:
                is_uniq      = self.spec.name.uuid()
                task_exists  = self.spec.name in tracker.specs
                return spec_disabled or not (is_uniq and task_exists)
            case _:
                return spec_disabled

    ##--| prepare

    def should_timeout(self) -> bool:
        """ Cancel if you've waited too long """
        return self.priority < 1

    def should_wait(self, *, tracker:WorkflowTracker_p) -> bool:
        """ if any dependencies have not run, delay this task  """
        should_wait : bool = False
        deps = tracker._dependency_states_of(self.spec.name)
        for dep, dep_state in deps:
            match dep_state:
                case x if x in TrAPI.SUCCESS_STATUSES:
                    pass
                case _:
                    tracker.queue(dep)
                    should_wait = True
        else:
            self.priority -= 1
            return should_wait

    ##--| run

    def should_skip(self, source:State) -> bool:  # noqa: ARG002
        """ run a task's depends_on group, coercing to a bool
        returns False if the runner should skip the rest of the task
        """
        match self._execute_action_group(group=API.DEPENDS_GROUP, lock_state=True): # type: ignore[attr-defined]
            case _, ActRE.SKIP | ActRE.FAIL:
                return True
            case _:
                return False

    def should_halt(self, *, tracker:WorkflowTracker_p) -> bool:
        # check for failed and halted tasks
        deps = tracker._dependency_states_of(self.spec.name)
        for _, dep_state in deps:
            match dep_state:
                case TaskStatus_e.HALTED | TaskStatus_e.FAILED:
                    return True
                case _:
                    pass
        else:
            return False

    def should_fail(self) -> bool:
        return False

    def state_is_needed(self, *, tracker:WorkflowTracker_p) -> bool:
        """ delays exit from teardown _internal_state until it is safe to do so """
        injs : set
        match tracker.specs[self.name]:
            case TrAPI.SpecMeta_d(injection_targets=set() as injs) if bool(injs):
                return True
            case _:
                return False

class _Callbacks_m:
    _internal_state           : dict
    name            : TaskName_p
    spec            : TaskSpec
    _state_history  : list

    def on_exit_state(self, *, source:Any) -> None:
        """ Keep track of the progression of the task """
        self._state_history.append(source.value)

    ##--| Standard Callbacks

    def on_enter_INIT(self, *, tracker:WorkflowTracker_p, parent:Maybe[TaskName_p]=None) -> None:  # noqa: N802
        """
        initialise _internal_state,
        possibly run injections?
        """
        _task : Task_p
        assert(hasattr(self, "param_specs"))
        ##--|
        internal_state = dict()
        ##--| Get parent data (for cleanup tasks
        match self._get_parent_data(tracker, parent):
            case None:
                pass
            case dict() as pdata:
                internal_state.update(pdata)
        ##--| apply CLI params
        match self._get_cli_data(tracker):
            case None:
                pass
            case dict() as cdata:
                # Apply CLI passed params, but only as the default
                # So if override values have been injected, they are preferred
                for x,y in cdata.items():
                    internal_state.setdefault(x, y)

        internal_state |= self._get_spec_data()

        ##--| apply late injections
        match self._get_inject_data(tracker):
            case None:
                pass
            case dict() as idata:
                internal_state.update(idata)

        ##--| validate
        match self.spec.extra.get(MUST_INJECT_K, None):
            case None:
                pass
            case [*xs] if bool(missing:=[x for x in xs if x not in internal_state]):
                raise doot.errors.TrackingError("Task did not receive required injections", self.spec.name, xs, self._internal_state.keys())

        if CLI_K in self._internal_state:
            del self._internal_state[CLI_K]
        ##--| Apply the state
        self._internal_state |= internal_state

        ##--| build late actions
        self.prepare_actions() # type: ignore[attr-defined]

    def on_enter_RUNNING(self, *, step:int, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        count : int
        logmod.debug("-- Executing Task %s: %s", step, self.spec.name[:])
        match self._execute_action_group(group=API.SETUP_GROUP): # type: ignore[attr-defined]
            case int() as count, ActRE.SKIP_GROUP:
                pass
            case int() as count, ActRE.SKIP | ActRE.SKIP_TASK:
                raise FSMSkip()
            case int() as count, ActRE():
                pass
            case x:
                raise TypeError(type(x))

        match self._execute_action_group(group=API.ACTION_GROUP): # type: ignore[attr-defined]
            case int() as count, ActRE() as res:
                pass
            case x:
                raise TypeError(type(x))

    def on_exit_RUNNING(self, *, step:int, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        # TODO Report on the task's actions
        pass

    def on_exit_TEARDOWN(self, *, source:Any, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        # source : the _internal_state the teardown was triggered from
        logmod.debug("-- Tearing Down Task : %s", self.spec.name[:])
        match self._execute_action_group(group=API.CLEANUP_GROUP): # type: ignore[attr-defined]
            case int() as count, ActRE():
                pass
            case x:
                raise TypeError(type(x))

        # Task is torn down, clear the _internal_state to remove its memory footprint
        self._internal_state.clear()

    ##--| Branched callbacks

    def on_enter_SUCCESS(self, *, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        pass

    def on_enter_FAILED(self, *, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        # Propagate failure to upstream tasks (as HALTs?)
        ##--|
        # Perform fail actions
        match self._execute_action_group(group=API.FAIL_GROUP): # type: ignore[attr-defined]
            case int() as count, ActRE() as res:
                pass
            case x:
                raise TypeError(type(x))

    def on_enter_HALTED(self, *, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        # Propagate halt to other upstream tasks
        for _, _ in tracker._successor_states_of(self.name):
            pass
        else:
            pass

    def on_enter_SKIPPED(self) -> None:  # noqa: N802
        pass

    ##--| internal

    def _get_parent_data(self, tracker:WorkflowTracker_p, parent:Maybe[TaskName_p]) -> Maybe[dict]:
        _task : Task_p
        match tracker.specs.get(parent, None):
            case TrAPI.SpecMeta_d(task=Task_p() as _task):
                logging.info("Applying Parent State")
                return _task.internal_state
            case _:
                return None

    def _get_cli_data(self, tracker:WorkflowTracker_p) -> Maybe[dict]:
        idx : int  = 0
        target     = self.spec.name.pop()[:,:]
        cli_args   = doot.args.on_fail({}).subs[target]()
        return cli_args

    def _get_spec_data(self) -> dict:
        data = dict(self.spec.extra)
        data |= {
            STATE_TASK_NAME_K  : self.spec.name,
            ACTION_STEP_K      : 0,
        }
        return data

    def _get_inject_data(self, tracker:WorkflowTracker_p) -> Maybe[dict]:
        match tracker.specs[self.spec.name]:
            case TaskName_p() as control, InjectSpec() as inj:
                logging.info("Applying Late Injections")
                control_task = tracker.specs[control].task
                # remove the injection from the registry
                tracker.specs[control].injection_targets.remove(self.spec.name)
                return inj.apply_from_state(control_task)
            case _:
                return None

##--|

@Proto(Task_i, API.TaskModel_p)
@Mixin(_Predicates_m, _Callbacks_m, _TaskActionPrep_m)
class FSMTask:
    """
    The implementation of a task, as the domain model for a TaskMachine
    """
    _default_flags   : ClassVar[set]  = set()
    step             : int
    spec             : TaskSpec
    status           : TaskStatus_e
    priority         : int
    records          : list[Any]
    _internal_state  : dict
    _state_history   : list[TaskStatus_e]

    def __init__(self, spec:TaskSpec):
        self.step        = -1
        self.spec        = spec
        self.priority    = self.spec.priority
        # TODO use taskstatus method for initial
        self.status          = TaskStatus_e.NAMED
        self._internal_state           = {}
        self._state_history  = []
        self.records         = []
        assert(self.priority > 0)

    @property
    def name(self) -> TaskName:
        return self.spec.name

    @property
    def internal_state(self) -> dict:
        return self._internal_state
    ##--| dunders

    @override
    def __repr__(self) -> str:
        cls  = self.__class__.__qualname__
        return f"<{cls}: {self.spec.name[:]}>"

    @override
    def __hash__(self) -> int:
        return hash(self.spec.name)

    @override
    def __eq__(self, other:object) -> bool:
        result : bool = False
        match other:
            case str() | TaskName():
                full      = self.spec.name
                readable  = self.spec.name[:]
                result    = other in {full, readable}
                return result
            case Task_p():
                result = self.spec.name == other.spec.name
            case _:
                pass

        return result

    ##--| internal

    def _execute_action_group(self, *, group:str, lock_state:bool=False) -> tuple[int, ActRE]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        x               : Any
        actions         : list[ActionSpec]
        group_result    : ActRE = ActRE.SUCCESS
        executed_count  : int = 0
        ##--|
        match self.get_action_group(group):
            case []:
                return executed_count, group_result
            case list() as actions:
                pass
            case x:
                raise TypeError(type(x))

        for action in actions:
            match action:
                case ActionSpec():
                    pass
                case _: # Ignore relationspecs
                    continue

            match self._execute_action(executed_count, action, group=group, lock_state=lock_state):
                case True | None:
                    continue
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.wf.line("Remaining Task Actions skipped by Action Result", char=".")
                    group_result = ActRE.SKIP
                    break
                case x:
                    raise TypeError(type(x))

            executed_count += 1

        ##--|
        return executed_count, group_result

    def _execute_action(self, count:int, action:ActionSpec, *, group:Maybe[str]=None, lock_state:bool=False) -> ActRE|bool|list[TaskSpec]:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result  : Maybe[bool|ActRE|dict|list]
        _internal_state   : ChainMap
        assert(callable(action))
        _internal_state = ChainMap({ACTION_STEP_K : count}, self._internal_state)
        match group:
            case str():
                doot.report.wf.act(f"Action: {self.step}.{group}.{count}", action.do)
            case None:
                doot.report.wf.act(f"Action: {self.step}.{count}", action.do)

        logging.debug("Action Executing for Task: %s", self.spec.name[:])
        logging.debug("Action State: %s.%s: args=%s kwargs=%s. _internal_state(size)=%s", self.step, count, action.args, dict(action.kwargs), len(self._internal_state.keys()))
        match (result:=action(_internal_state)):
            case None | True:
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                raise doot.errors.TaskFailed("Task %s: Action Failed: %s", self.spec.name[:], action.do, task=self.spec)
            case ActRE.SKIP:
                # result will be returned, and expand_job/execute_task will handle it
                doot.report.wf.result(["Skip"])
            case dict(): # update the task's _internal_state
                _internal_state.update({str(k):v for k,v in result.items()})
                result = ActRE.SUCCESS
            case list() if all(isinstance(x, TaskName_p|TaskSpec_i|DelayedSpec) for x in result):
                pass
            case _:
                raise doot.errors.TaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", self.spec.name[:], action.do, result, task=self.spec)

        match lock_state:
            case True:
                pass
            case False:
                self._internal_state |= _internal_state

        return result

    def get_action_group(self, group_name:str) -> list[ActionSpec]:
        if hasattr(self, group_name):
            return getattr(self, group_name) # type: ignore[no-any-return]
        if hasattr(self.spec, group_name):
            return getattr(self.spec, group_name) # type: ignore[no-any-return]

        logging.warning("Unknown Groupname: %s", group_name)
        return []

    ##--| public

    def param_specs(self) -> list:
        return []

    def log(self, msg:str, level:int=logmod.DEBUG, prefix:Maybe[str]=None) -> None:
        pass

class FSMJob(FSMTask):
    """
    Extends an FSMTask for running a job
    """

    def on_enter_RUNNING(self, step:int, tracker:WorkflowTracker_p) -> None:  # noqa: N802
        """ Modifies how the object runs,

        requires the main action group return a list of tasks/specs

        """
        logmod.debug("-- Expanding Job %s: %s", step, self.spec.name[:])
        match self._execute_action_group(group=API.SETUP_GROUP): # type: ignore[attr-defined]
            case int() as x, ActRE.SKIP_GROUP:
                pass
            case int() as x, ActRE.SKIP | ActRE.SKIP_TASK:
                raise FSMSkip()
            case int() as x, ActRE():
                pass
            case x:
                raise TypeError(type(x))

        match self._execute_expansion_group(group=API.ACTION_GROUP):
            case int() as count, [*xs]: # Queue new subtasks
                for x in xs:
                    tracker.queue(x, parent=self.spec.name)
                else:
                    tracker.build_network()
            case x:
                raise TypeError(type(x))

    def _execute_expansion_group(self, *, group:str) -> tuple[int, list[TaskSpec]]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actions         : list[ActionSpec]
        to_queue        : list[TaskSpec]  = []
        executed_count  : int             = 0
        ##--|
        match self.get_action_group(group):
            case []:
                return executed_count, to_queue
            case list() as actions:
                pass
            case x:
                raise TypeError(type(x))

        for action in actions:
            match action:
                case ActionSpec():
                    pass
                case _:
                    continue

            match self._execute_action(executed_count, action, group=group, lock_state=False):
                case True | None:
                    continue
                case list() as result:
                    to_queue += result
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    doot.report.gen.line("Remaining Task Actions skipped by Action Result", char=".")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        ##--|
        return executed_count, to_queue
