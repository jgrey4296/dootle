#!/usr/bin/env python3
"""

"""
# ruff: noqa: E402, B011, ANN202, ERA001, ANN001
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import unittest
import warnings
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow import TaskSpec, TaskName
from doot.util import mock_gen

# ##-- end 1st party imports

from doot.workflow._interface import Task_i, TaskStatus_e
from doot.workflow._interface import ActionResponse_e as ActRE
from ..machines import TaskMachine
from ..task import FSMTask
from ..errors import FSMSkip, FSMHalt
from ..fsm_tracker import FSMTracker

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
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot.workflow._interface import Task_p, TaskStatus_e
# isort: on
# ##-- end types

logging = logmod.root
logmod.getLogger("jgdv").propagate = False

##-- util actions

def skip_action(*args, **kwargs) -> ActRE:
    return ActRE.SKIP

def fail_action(*args, **kwargs) -> ActRE:
    return ActRE.FAIL

##-- end util actions

class TestStateTracker_Basic:

    def test_sanity(self):
        assert(True)
        assert(not False)

    def test_basic(self):
        obj = FSMTracker()
        assert(isinstance(obj, FSMTracker))

    @pytest.mark.skip
    def test_queue_task(self):
        obj   = FSMTracker()
        spec  = obj._factory.build({"name":"simple::task"})
        match obj.queue(spec):
            case TaskName() as x:
                assert(x in obj._registry.tasks)
                assert(isinstance(obj._registry.tasks[x], Task_p))
                assert(x in obj.machines)
            case x:
                assert(False), x

    def test_instantiate_task(self):
        obj        = FSMTracker()
        spec       = obj._factory.build({"name":"simple::task"})
        obj.register(spec)
        inst_name  = obj._instantiate(spec.name)
        obj._instantiate(inst_name, task=True)
        assert(inst_name in obj._registry.tasks)
        assert(isinstance(obj._registry.tasks[inst_name], Task_p))
        assert(inst_name in obj.machines)
        assert(obj.machines[inst_name].current_state_value == TaskStatus_e.INIT)

    def test_next_for(self):
        obj   = FSMTracker()
        spec  = obj._factory.build({"name":"simple::task", "ctor": FSMTask})
        obj.queue(spec)
        obj.build()
        inst_name = obj.concrete[spec.name][0]
        assert(obj.machines[inst_name].current_state_value == TaskStatus_e.INIT)
        match obj.next_for():
            case Task_p() as x:
                assert(x.name == "simple::task[<uuid>]")
                assert(x.name in obj.machines)
                assert(True)
            case x:
                assert(False), x

class TestStateTracker_NextFor:

    @pytest.fixture(scope="function")
    def tracker(self):
        return FSMTracker()

    @pytest.fixture(scope="function")
    def spec(self, tracker):
        """ A Simple task spec """
        return tracker._factory.build({
            "name" : "basic::Task",
            "ctor" : FSMTask,
        })

    @pytest.fixture(scope="function")
    def specdep(self, tracker):
        """ a spec with a dependency """
        spec = tracker._factory.build({
            "name"        : "basic::alpha",
            "depends_on"  : ["basic::dep"],
            "ctor"        : FSMTask,
        })
        dep  = tracker._factory.build({
            "name" : "basic::dep",
            "ctor" : FSMTask,
        })
        return spec, dep

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_for_fails_with_unbuilt_network(self, tracker):
        with pytest.raises(doot.errors.TrackingError):
            tracker.next_for()

    def test_for_empty(self, tracker):
        tracker.build()
        assert(tracker.next_for() is None)

    def test_for_no_connections(self, tracker, spec):
        tracker.register(spec)
        t_name = tracker.queue(spec.name)
        tracker.build()
        match tracker.next_for():
            case Task_p():
                assert(tracker.get_status(target=t_name) is TaskStatus_e.READY)
            case x:
                assert(False), x
        # Now theres nothing remaining
        match tracker.next_for():
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_simple_dependendency(self, tracker, specdep):
        spec, dep = specdep
        tracker.register(spec, dep)
        t_name = tracker.queue(spec.name, from_user=True)
        tracker.build()
        assert(t_name in tracker._registry.tasks)
        assert(dep.name in tracker._registry.concrete)
        match tracker.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(tracker.get_status(target=result.name) is TaskStatus_e.READY)
            case x:
                assert(False), x
        assert(tracker.get_status(target=t_name) is TaskStatus_e.WAIT)

    def test_dependency_success_produces_ready_state(self, tracker, specdep):
        spec, dep = specdep
        tracker.register(spec, dep)
        t_name = tracker.queue(spec.name, from_user=True)
        tracker.build()
        # Get the dep and run it
        dep_inst = tracker.next_for()
        assert(dep.name < dep_inst.name)
        assert(isinstance(tracker.machines[dep_inst.name].model, FSMTask))
        tracker.machines[dep_inst.name](step=1, tracker=tracker)
        assert(tracker.get_status(target=dep_inst.name) is TaskStatus_e.TEARDOWN)
        # Now check the top is no longer blocked
        assert(tracker.get_status(target=t_name) is TaskStatus_e.WAIT)
        tracker.machines[t_name](step=1, tracker=tracker, until=[TaskStatus_e.READY])
        assert(tracker.get_status(target=t_name) is TaskStatus_e.READY)

class TestStateTracker_Pathways:

    @pytest.fixture(scope="function")
    def tracker(self):
        return FSMTracker()

    def test_skip_in_action_group__single_step(self, tracker):
        """
        Running the task with a skip action raises FSMSkip
        """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "setup" : [{"do":skip_action}],
            "ctor" : FSMTask,
        })
        t_inst  : TaskName  = tracker.queue(spec)
        tracker.build()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]

        machine(step=1, tracker=tracker)
        assert(machine.current_state_value == TaskStatus_e.TEARDOWN)

    def test_skip_in_depends_on_group__single_step(self, tracker):
        """
        Running the task with a skip action raises FSMSkip
        """
        spec = tracker._factory.build({
            "name"        : "simple::basic",
            "depends_on"  : [{"do":skip_action}],
            "ctor"        : FSMTask,
        })
        t_inst  : TaskName  = tracker.queue(spec)
        tracker.build()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]
        machine.run(step=1, tracker=tracker)
        match machine.current_state_value:
            case TaskStatus_e.SKIPPED:
                assert(True)
            case x:
                assert(False), x

    def test_skip__full(self, tracker):
        """
        Calling the machine with a skip action jumps to teardown state
        """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "setup" : [{"do":skip_action}],
            "ctor" : FSMTask,
        })
        t_inst  : TaskName  = tracker.queue(spec)
        tracker.build()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]

        match machine(step=1, tracker=tracker):
            case TaskStatus_e.TEARDOWN:
                assert(True)
            case x:
                assert(False), x

    @pytest.mark.xfail
    def test_halt(self, mocker, tracker):
        """ Force a Halt """
        spec = tracker._factory.build({"name":"basic::alpha",
                               "depends_on":["basic::dep"],
                               "ctor":"dootle.control.fsm.task:FSMTask"})
        dep  = tracker._factory.build({"name":"basic::dep",
                               "ctor":"dootle.control.fsm.task:FSMTask"})
        tracker.register(spec, dep)
        t_name   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=t_name) is TaskStatus_e.INIT)
        tracker.build()
        match tracker.next_for():
            case Task_p() as x:
                assert(x.name == dep_inst)
                x.should_halt = mocker.Mock(return_value=True)
                tracker.machines[x.name](step=1, tracker=tracker)
                assert(tracker.get_status(target=x.name) == TaskStatus_e.HALTED)
            case x:
                assert(False), x

    def test_fail(self, tracker):
        """ An action that fails shunts to teardown """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "actions" : [{"do":fail_action}],
            "ctor" : FSMTask,
        })
        t_inst  : TaskName  = tracker.queue(spec)
        tracker.build()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]
        match machine(step=1, tracker=tracker):
            case TaskStatus_e.TEARDOWN:
                assert(True)
            case x:
                assert(False), x

    @pytest.mark.xfail
    def test_success(self, tracker):
        pass

    @pytest.mark.xfail
    def test_teardown(self, tracker):
        pass
