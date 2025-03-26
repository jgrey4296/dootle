#!/usr/bin/env python3
"""

"""
# ruff: noqa: N812
# mypy: disable-error-code="attr-defined"
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
from collections import defaultdict
from contextlib import nullcontext
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import networkx as nx
from jgdv.debugging import SignalHandler
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot.enums import ActionResponse_e as ActRE
from doot.enums import Report_f, TaskStatus_e
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec

from . import _runner_util as RU

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv.reporter._interface import AltReporter_p
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot._abstract import (Action_p, Job_p, Reporter_p, Task_p, TaskRunner_p, TaskTracker_p)
# isort: on
# ##-- end types

##-- logging
logging           = logmod.getLogger(__name__)
printer           = doot.subprinter()
setup_l           = doot.subprinter("setup")
report_l          = doot.subprinter("report")
taskloop_l        = doot.subprinter("task_loop")
fail_l            = doot.subprinter("fail").prefix(doot.constants.printer.fail_prefix)
artifact_l        = doot.subprinter("artifact")
success_l         = doot.subprinter("success")
skip_l            = doot.subprinter("skip")
in_task_header_l  = doot.subprinter("task_header")
out_task_header_l = in_task_header_l.prefix("< ")
actgrp_l          = doot.subprinter("action_group").prefix(doot.constants.printer.action_group_prefix)
queue_l           = doot.subprinter("queue")
actexec_l         = doot.subprinter("action_exec")
state_l           = doot.subprinter("task_state")
##-- end logging

skip_msg             : Final[str]       = doot.constants.printer.skip_by_condition_msg
max_steps            : Final[int]       = doot.config.on_fail(100_000).settings.tasks.max_steps()
dry_run              : Final[bool]      = doot.args.on_fail(False).cmd.args.dry_run()  # noqa: FBT003
fail_prefix          : Final[str]       = doot.constants.printer.fail_prefix
loop_entry_msg       : Final[str]       = doot.constants.printer.loop_entry
loop_exit_msg        : Final[str]       = doot.constants.printer.loop_exit

DEFAULT_SLEEP_LENGTH : Final[int|float] = doot.config.on_fail(0.2, int|float).startup.sleep.task()
##--|

class _ActionExecution_m:
    """ Covers the nuts and bolts of executing an action group """

    def _execute_action_group(self, task:Task_p, *, allow_queue:bool=False, group:Maybe[str]=None) -> Maybe[tuple[int, ActRE]]:
        """ Execute a group of actions, possibly queue any task specs they produced,
        and return a count of the actions run + the result
        """
        actions = task.get_action_group(group)

        if not bool(actions):
            return None

        group_result              = ActRE.SUCCESS
        to_queue : list[TaskSpec] = []
        executed_count            = 0

        for action in actions:
            if self._skip_relation_specs(action):
                continue

            match self._execute_action(executed_count, action, task):
                case True | None:
                    continue
                case list() as result:
                    to_queue += result
                case False:
                    group_result = ActRE.FAIL
                    break
                case ActRE.SKIP:
                    self.report.pause("Skip Rest")
                    group_result = ActRE.SKIP
                    break

            executed_count += 1

        else: # no break.
            match self._maybe_queue_more_tasks(to_queue, allowed=allow_queue):
                case None:
                    pass
                case x:
                    group_result = x

        return executed_count, group_result

    def _skip_relation_specs(self, action:RelationSpec|ActionSpec) -> bool:
        """ return of True signals the action is a relationspec, so is to be ignored """
        match action:
            case RelationSpec():
                return True
            case ActionSpec():
                return False
            case _:
                raise doot.errors.TaskError("Task Failed: Bad Action: %s", repr(action))

    def _maybe_queue_more_tasks(self, new_tasks:list, *, allowed:bool=False) -> Maybe[ActRE]:
        """ When 'allowed', an action group can queue more tasks in the tracker,
        can return a new ActRE to describe the result status of this group
        """
        if bool(new_tasks) and not allowed:
            self.report.fail("Tried to Queue additional tasks from a bad action group")
            return ActRE.FAIL

        new_nodes = []
        failures  = []
        for spec in new_tasks:
            match self.tracker.queue_entry(spec):
                case None:
                    failures.append(spec.name)
                case TaskName() as x:
                    new_nodes.append(x)

        if bool(failures):
            self.report.fail(f"Queuing a generated specs failed: {failures}")
            return ActRE.FAIL

        if bool(new_nodes):
            self.tracker.build_network(sources=new_nodes)
            queue_l.trace("Queued %s Subtasks", len(new_nodes))

        return None

    def _execute_action(self, count:int, action:Action_p, task:Task_p) -> ActRE|list:
        """ Run the given action of a specific task.

          returns either a list of specs to (potentially) queue,
          or an ActRE describing the action result.

        """
        result                     = None
        task.state['_action_step'] = count
        self.report.act(action)
        result = action(task.state)

        match result:
            case None | True:
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                self.report.fail(action)
                raise doot.errors.TaskFailed("Task %s: Action Failed: %s", task.shortname, action.do, task=task.spec)
            case ActRE.SKIP:
                # result will be returned, and expand_job/execute_task will handle it
                pass
            case dict(): # update the task's state
                self.report.state_result()
                task.state.update({str(k):v for k,v in result.items()})
                result = ActRE.SUCCESS
            case list() if all(isinstance(x, TaskName|TaskSpec) for x in result):
                pass
            case _:
                self.report.fail(action)
                raise doot.errors.TaskError("Task %s: Action %s Failed: Returned an unplanned for value: %s", task.shortname, action.do, result, task=task.spec)

        self.report.result(action)
        return result

class _RunnerCtx_m:

    _signal_failure : Maybe[doot.errors.DootError]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._enter_msg      = loop_entry_msg
        self._exit_msg       = loop_exit_msg
        self._signal_failure = None

    def __enter__(self) -> Self:
        setup_l.info("Building Task Network...")
        self.tracker.build_network()
        setup_l.info("Task Network Built. %s Nodes, %s Edges, %s Edges from Root.",
                     len(self.tracker.network.nodes), len(self.tracker.network.edges), len(self.tracker.network.pred[self.tracker._root_node]))
        setup_l.info("Validating Task Network...")
        self.tracker.validate_network()
        setup_l.info("Validation Complete")
        taskloop_l.info(self._enter_msg, extra={"colour" : "green"})
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> Literal[False]:
        logging.info("---- Exiting Runner Control")
        # TODO handle exc_types?
        printer.setLevel("INFO")
        taskloop_l.info("")
        taskloop_l.info(self._exit_msg, extra={"colour":"green"})
        self._finish()
        return False

    def _finish(self) -> None:
        """finish running tasks, summarizing results using the reporter
          separate from __exit__ to allow it to be overridden
        """
        logging.info("---- Running Completed")
        if self.step >= max_steps:
            report_l.warning("Runner Hit the Step Limit: %s", max_steps)

        self.report.summary()
        match self._signal_failure:
            case None:
                return
            case doot.errors.DootError():
                raise self._signal_failure

class _RunnerHandlers_m:

    def _handle_task_success[T:Maybe[Task_p|TaskArtifact]](self, task:T) -> T:
        """ The basic success handler. just informs the tracker of the success """
        success_l.debug("(Task): %s", task)
        match task:
            case None:
                pass
            case _:
                self.tracker.set_status(task, TaskStatus_e.SUCCESS)
        return task

    def _handle_failure(self, failure:Exception) -> None:
        """ The basic failure handler.
          Triggers a breakpoint on Interrupt,
          otherwise informs the tracker of the failure.

          Halts any failed or errored tasks, which propagates to any successors
          Fails any DootErrors, TrackingErrors, and non-doot errors

          the tracker handle's clearing itself and shutting down
        """
        self._signal_failure : Maybe[doot.errors.DootError]
        match failure:
            case doot.errors.Interrupt():
                breakpoint()
                pass
            case doot.errors.TaskFailed() as err:
                self._signal_failure = err
                fail_l.warning("%s Halting: %s", fail_prefix, err)
                self.tracker.set_status(err.task, TaskStatus_e.HALTED)
            case doot.errors.TaskError() as err:
                self._signal_failure = err
                self.tracker.set_status(err.task, TaskStatus_e.FAILED)
                raise err
            case doot.errors.TrackingError() as err:
                self._signal_failure = err
                raise err
            case doot.errors.DootError() as err:
                self._signal_failure = err
                raise err
            case err:
                self._signal_failure = doot.errors.DootError("Unknown Failure")
                fail_l.exception("%s Unknown failure occurred: %s", fail_prefix, failure)
                raise err

    def _notify_artifact(self, art:TaskArtifact) -> None:
        """ A No-op for when the tracker gives an artifact """
        self.report.act("actifact", art)
        raise doot.errors.StateError("Artifact resolutely does not exist", art)

##--|

@Proto(TaskRunner_p, check=False)
@Mixin(_ActionExecution_m, _RunnerCtx_m, _RunnerHandlers_m, RU._RunnerSleep_m)
class AltRepRunner:
    """ The simplest single threaded task runner """

    step          : int
    tracker       : TaskTracker_p
    reporter      : AltReporter_p
    teardown_list : list

    def __init__(self:Self, *, tracker:TaskTracker_p, reporter:AltReporter_p):
        super().__init__()
        self.step          = 0
        self.tracker       = tracker
        self.report        = reporter
        self.teardown_list = [] # list of tasks to teardown

    def __call__(self, *tasks:str, handler:Maybe[Callable]=None): #noqa: ARG002
        """ tasks are initial targets to run.
          so loop on the tracker, getting the next task,
          running its actions,
          and repeating,
          until done

          if task is a job, it is expanded and added into the tracker
          """
        match handler:
            case None | True:
                handler = SignalHandler()
            case type() as x:
                handler = x()
            case x if hasattr(x, "__enter__"):
                handler = x
            case _:
                handler = nullcontext()

        with handler:
            self.report.root()
            while bool(self.tracker) and self.step < max_steps:
                self._run_next_task()
            else:
                self.report.finished()

    def _run_next_task(self) -> None:
        """
          Get the next task from the tracker, expand/run it,
          and handle the result/failure
        """
        task = None
        try:
            match (task:=self.tracker.next_for()):
                case None:
                    pass
                case TaskArtifact():
                    self._notify_artifact(task)
                case Job_p():
                    self._expand_job(task)
                case Task_p():
                    self._execute_task(task)
                case x:
                    self.report.fail(f"Unknown Value provided to runner: {x}")
        except doot.errors.TaskError as err:
            assert(isinstance(task, Task_p))
            err.task = task
            self._handle_failure(err)
        except doot.errors.DootError as err:
            self._handle_failure(err)
        except Exception as err:
            self.tracker.clear_queue()
            raise
        else:
            self._handle_task_success(task)
            self._sleep(task)
            self.step += 1

    def _expand_job(self, job:Job_p) -> None:
        """ turn a job into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Job %s: %s", self.step, job.shortname)
        assert(isinstance(job, Job_p))
        try:
            if not self._test_conditions(job):
                self.report.result(skip_msg.format(self.step, job.shortname))
                return

            self.report.branch(job.spec.name)

            self._execute_action_group(job, group="setup")
            self._execute_action_group(job, allow_queue=True, group="actions")

        except doot.errors.DootError as err:
            self._execute_action_group(job, group="on_fail")
            raise
        finally:
            self.report.result()

    def _execute_task(self, task:Task_p) -> None:
        """ execute a single task's actions """
        logmod.debug("-- Expanding Task %s: %s", self.step, task.shortname)
        assert(not isinstance(task, Job_p))
        skip_task = False
        try:
            skip_task = not self._test_conditions(task)
            if skip_task:
                self.report.result("skip")
                return

            self.report.branch(task.spec.name)
            self._execute_action_group(task, group="setup")
            self._execute_action_group(task, group="actions")
        except doot.errors.DootError as err:
            skip_task = True
            self._execute_action_group(task, group="on_fail")
            raise
        else:
            if skip_task:
                self.report.result("skipped")
            else:
                self.report.result(task.spec.name)

    def _test_conditions(self, task:Task_p) -> bool:
        """ run a task's depends_on group, coercing to a bool
        returns False if the runner should skip the rest of the task
        """
        self.act("?", "Preconditions")
        match self._execute_action_group(task, group="depends_on"):
            case None:
                return True
            case _, ActRE.SKIP | ActRE.FAIL:
                return False
            case _:
                return True
