#!/usr/bin/env python3
"""

"""
# ruff: noqa: B011, ANN202, ANN001, ANN002, ARG001, ANN003
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

from doot.workflow._interface import Task_i, TaskStatus_e, TaskSpec_i, TaskName_p
from doot.workflow._interface import Task_p
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
# isort: on
# ##-- end types

logging = logmod.root
logmod.getLogger("jgdv").propagate = False
logmod.getLogger("jgdv.util").propagate = False
logmod.getLogger("doot.control").propagate = False

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

    def test_register(self):
        obj   = FSMTracker()
        spec  = obj._factory.build({"name":"simple::task"})
        assert(isinstance(spec, TaskSpec_i))
        assert(not bool(obj.specs))
        obj.register(spec)
        assert(bool(obj.specs))
        assert(not bool(obj.machines))

    def test_queue_task(self):
        obj   = FSMTracker()
        spec  = obj._factory.build({"name":"simple::task"})
        match obj.queue(spec):
            case TaskName_p() as x:
                assert(x in obj.specs)
                assert(isinstance(obj.specs[x].task, Task_p))
                assert(x in obj.machines)
            case x:
                assert(False), x

    def test_instantiate_task(self):
        obj        = FSMTracker()
        spec       = obj._factory.build({"name":"simple::task"})
        obj.register(spec)
        inst_name  = obj._instantiate(spec.name)
        obj._instantiate(inst_name, task=True)
        assert(inst_name in obj.specs)
        assert(isinstance(obj.specs[inst_name].task, Task_p))
        assert(inst_name in obj.machines)
        assert(obj.machines[inst_name].current_state_value == TaskStatus_e.INIT)

    def test_next_for(self):
        obj   = FSMTracker()
        spec  = obj._factory.build({"name":"simple::task", "ctor": FSMTask})
        instance = obj.queue(spec, from_user=True)
        obj.build()
        assert(obj.machines[instance].current_state_value == TaskStatus_e.INIT)
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

    @pytest.mark.xfail
    def test_for_fails_with_unbuilt_network(self, tracker):
        with pytest.raises(doot.errors.TrackingError):
            tracker.next_for()

    def test_for_empty(self, tracker):
        tracker.build()
        assert(tracker.next_for() is None)

    def test_for_no_connections(self, tracker, spec):
        tracker.register(spec)
        t_name = tracker.queue(spec.name, from_user=True)
        tracker.build()
        tracker.validate()
        match tracker.next_for():
            case Task_p():
                assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.READY)
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
        assert(t_name in tracker.specs)
        assert(dep.name in tracker.concrete)
        match tracker.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(tracker.get_status(target=result.name)[0] is TaskStatus_e.READY)
            case x:
                assert(False), x
                assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.WAIT)

    def test_dependency_success_produces_ready_state(self, tracker, specdep):
        spec, dep          = specdep
        expected_priority  = 10
        tracker.register(spec, dep)
        t_name = tracker.queue(spec.name, from_user=True)
        assert(tracker.get_status(target=t_name)[1] == expected_priority)
        tracker.build()
        # Get the dep and run it
        dep_inst = tracker.next_for()
        assert(dep.name < dep_inst.name)
        assert(isinstance(tracker.machines[dep_inst.name].model, FSMTask))
        tracker.machines[dep_inst.name](step=1, tracker=tracker)
        assert(tracker.get_status(target=dep_inst.name)[0] is TaskStatus_e.TEARDOWN)
        # Now check the top is no longer blocked
        assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.WAIT)
        logging.debug("-------")
        tracker.machines[t_name](step=1, tracker=tracker, until=[TaskStatus_e.READY])
        assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.READY)


class TestStateTracker_Pathways:

    @pytest.fixture(scope="function")
    def tracker(self):
        return FSMTracker()

    def test_skip_in_action_group__single_step(self, tracker) -> None:
        """
        Running the task with a skip action in setup skips the entire task
        """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "setup" : [{"do":skip_action}],
        })
        t_inst  : TaskName_p = tracker.queue(spec, from_user=True)
        tracker.build()
        tracker.validate()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]

        machine(step=1, tracker=tracker)
        assert(machine.current_state_value == TaskStatus_e.TEARDOWN)
        assert(task._state_history[-1] == TaskStatus_e.SKIPPED)

    def test_skip_in_depends_on_group__single_step(self, tracker) -> None:
        """
        Running the task with a skip action in dependencies skips the running internal_state
        """
        spec = tracker._factory.build({
            "name"        : "simple::basic",
            "depends_on"  : [{"do":skip_action}],
            "ctor"        : FSMTask,
        })
        t_inst  : TaskName_p  = tracker.queue(spec, from_user=True)
        tracker.build()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]
        machine.run(step=1, tracker=tracker)
        match machine.current_state_value:
            case TaskStatus_e.SKIPPED:
                assert(TaskStatus_e.RUNNING not in task._state_history)
                assert(task._state_history[-1] == TaskStatus_e.READY)
            case x:
                assert(False), x

    def test_skip__full(self, tracker) -> None:
        """
        Calling the machine with a skip action jumps to teardown internal_state
        """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "setup" : [{"do":skip_action}],
            "ctor" : FSMTask,
        })
        t_inst  : TaskName_p  = tracker.queue(spec, from_user=True)
        tracker.build()
        tracker.validate()
        task    : Task_i    = tracker.next_for()
        assert(task.spec.name == t_inst)
        assert(task.status == TaskStatus_e.READY)
        machine = tracker.machines[t_inst]

        match machine(step=1, tracker=tracker):
            case TaskStatus_e.TEARDOWN:
                assert(task._state_history[-1] == TaskStatus_e.SKIPPED)
            case x:
                assert(False), x

    def test_halt(self, tracker) -> None:
        """ Force a Halt """
        class HaltingTask(FSMTask):
            def should_halt(self):
                return True

        tracker._factory.task_ctor = HaltingTask
        spec = tracker._factory.build({"name":"basic::alpha",
                                       "depends_on":["basic::dep"],
                                       })
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        t_name   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.INIT)
        tracker.build()
        match tracker.next_for():
            case Task_p() as x:
                assert(x.name == dep_inst)
                tracker.machines[x.name](step=1, tracker=tracker)
                assert(tracker.get_status(target=x.name)[0] is TaskStatus_e.TEARDOWN)
                assert(x._state_history[-1] == TaskStatus_e.HALTED)
            case x:
                assert(False), x

    def test_fail(self, tracker) -> None:
        """ An action that fails shunts to teardown """
        spec = tracker._factory.build({
            "name" : "simple::basic",
            "actions" : [{"do":fail_action}],
            "ctor" : FSMTask,
        })
        t_inst  : TaskName_p  = tracker.queue(spec, from_user=True)
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

    def test_success(self, tracker):
        """ run the task normally """
        spec = tracker._factory.build({"name":"basic::alpha",
                                       "depends_on":["basic::dep"],
                                       })
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        t_name   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.INIT)
        tracker.build()
        match tracker.next_for():
            case Task_p() as x:
                assert(x.name == dep_inst)
                tracker.machines[x.name](step=1, tracker=tracker)
                assert(tracker.get_status(target=x.name)[0] is TaskStatus_e.TEARDOWN)
                assert(x._state_history[-1] == TaskStatus_e.SUCCESS)
            case x:
                assert(False), x


    def test_teardown(self, tracker):
        """ run the task normally, then tear it down """
        spec = tracker._factory.build({"name":"basic::alpha",
                                       "depends_on":["basic::dep"],
                                       })
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        t_name   = tracker.queue(spec.name, from_user=True)
        dep_inst = tracker.queue(dep.name)
        assert(tracker.get_status(target=t_name)[0] is TaskStatus_e.INIT)
        tracker.build()
        task = tracker.next_for()
        tracker.machines[task.name](step=1, tracker=tracker)
        assert(tracker.get_status(target=task.name)[0] is TaskStatus_e.TEARDOWN)
        assert(task._state_history[-1] == TaskStatus_e.SUCCESS)
        # now run the teardown
        tracker.machines[task.name](tracker=tracker)
        assert(tracker.get_status(target=task.name)[0] is TaskStatus_e.DEAD)
        assert(task._state_history[-1] == TaskStatus_e.TEARDOWN)


    def test_teardown_wait(self, tracker):
        """ delay teardown until there are no injections relying on it """
        spec = tracker._factory.build({"name":"basic::alpha",
                                       "depends_on":["basic::dep"],
                                       })
        dep  = tracker._factory.build({"name":"basic::dep"})
        tracker.register(spec, dep)
        instance  = tracker.queue(spec.name, from_user=True)
        dep_inst  = tracker.queue(dep.name)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.INIT)
        tracker.build()
        # artificially set instance to inject into dep_inst
        tracker.specs[instance].injection_targets.add(dep_inst)
        # now run the instance
        tracker.machines[instance](step=2, tracker=tracker)
        assert(tracker.get_status(target=instance)[0] is TaskStatus_e.TEARDOWN)
        # Does not progress past teardown
        for _ in range(5):
            tracker.machines[instance](tracker=tracker)
            assert(tracker.get_status(target=instance)[0] is TaskStatus_e.TEARDOWN)
        else:
            # until dep_inst is removed
            tracker.specs[instance].injection_targets.remove(dep_inst)
            tracker.machines[instance](tracker=tracker)
            assert(tracker.get_status(target=instance)[0] is TaskStatus_e.DEAD)
            assert(tracker.machines[instance].model._state_history[-1] is TaskStatus_e.TEARDOWN)
            # The task internal internal_state is cleaned up
            assert(not bool(tracker.machines[instance].model.internal_state))
