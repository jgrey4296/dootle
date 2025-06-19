#!/usr/bin/env python3
"""

"""
# ruff: noqa: E402, B011, ANN202, ERA001
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

from doot.workflow._interface import Task_i
from ..machines import TaskTrackMachine
from ..task import FSMTask
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

class TestStateTracker_Basic:

    def test_sanity(self):
        assert(True)
        assert(not False)

    def test_basic(self):
        obj = FSMTracker()
        assert(isinstance(obj, FSMTracker))

    def test_queue_task(self):
        obj   = FSMTracker()
        spec  = TaskSpec.build({"name":"simple::task", "ctor":"dootle.control.fsm.task:FSMTask"})
        match obj.queue_entry(spec):
            case TaskName() as x:
                assert(x in obj._registry.tasks)
                assert(isinstance(obj._registry.tasks[x], Task_p))
                assert(x in obj.machines)
            case x:
                assert(False), x

    def test_next_for(self):
        obj   = FSMTracker()
        spec  = TaskSpec.build({"name":"simple::task", "ctor":"dootle.control.fsm.task:FSMTask"})
        obj.queue_entry(spec)
        obj.build_network()
        match obj.next_for():
            case Task_p() as x:
                assert(x.name == "simple::task[<uuid>]")
                assert(x.name in obj.machines)
                assert(True)
            case x:
                assert(False), x

class TestStateTracker_NextFor:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_for_fails_with_unbuilt_network(self):
        obj = FSMTracker()
        with pytest.raises(doot.errors.TrackingError):
            obj.next_for()

    def test_for_empty(self):
        obj = FSMTracker()
        obj.build_network()
        assert(obj.next_for() is None)

    def test_for_no_connections(self):
        obj  = FSMTracker()
        spec = TaskSpec.build({"name":"basic::Task", "ctor":"dootle.control.fsm.task:FSMTask"})
        obj.register_spec(spec)
        t_name = obj.queue_entry(spec.name)
        obj.build_network()
        match obj.next_for():
            case Task_p():
                assert(obj.get_status(t_name) is TaskStatus_e.READY)
            case x:
                assert(False), x
        # Now theres nothing remaining
        match obj.next_for():
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_simple_dependendency(self):
        obj  = FSMTracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"], "ctor":"dootle.control.fsm.task:FSMTask"})
        dep  = TaskSpec.build({"name":"basic::dep", "ctor":"dootle.control.fsm.task:FSMTask"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        obj.build_network()
        assert(t_name in obj._registry.tasks)
        assert(dep.name in obj._registry.concrete)
        match obj.next_for():
            case Task_p() as result:
                assert(dep.name < result.name)
                assert(obj.get_status(result.name) is TaskStatus_e.READY)
            case x:
                assert(False), x
        assert(obj.get_status(t_name) is TaskStatus_e.WAIT)

    def test_dependency_success_produces_ready_state_(self):
        obj  = FSMTracker()
        spec = TaskSpec.build({"name":"basic::alpha", "depends_on":["basic::dep"], "ctor":"dootle.control.fsm.task:FSMTask"})
        dep  = TaskSpec.build({"name":"basic::dep", "ctor":"dootle.control.fsm.task:FSMTask"})
        obj.register_spec(spec, dep)
        t_name = obj.queue_entry(spec.name, from_user=True)
        obj.build_network()
        # Get the dep and run it
        dep_inst = obj.next_for()
        assert(dep.name < dep_inst.name)
        obj.machines[dep_inst.name](step=1, tracker=obj)
        assert(obj.get_status(dep_inst.name) is TaskStatus_e.TEARDOWN)
        # Now check the top is no longer blocked
        match obj.next_for():
            case Task_p() as result:
                assert(spec.name < result.name)
                assert(result.name in obj.machines)
                assert(obj.get_status(result.name) is TaskStatus_e.READY)
            case x:
                assert(False), x


    @pytest.mark.xfail
    def test_halt(self, mocker):
        """ Force a Halt """
        obj  = FSMTracker()
        spec = TaskSpec.build({"name":"basic::alpha",
                               "depends_on":["basic::dep"],
                               "ctor":"dootle.control.fsm.task:FSMTask"})
        dep  = TaskSpec.build({"name":"basic::dep",
                               "ctor":"dootle.control.fsm.task:FSMTask"})
        obj.register_spec(spec, dep)
        t_name   = obj.queue_entry(spec.name, from_user=True)
        dep_inst = obj.queue_entry(dep.name)
        assert(obj.get_status(t_name) is TaskStatus_e.INIT)
        obj.build_network()
        match obj.next_for():
            case Task_p() as x:
                assert(x.name == dep_inst)
                x.should_halt = mocker.Mock(return_value=True)
                obj.machines[x.name](step=1, tracker=obj)
                assert(obj.get_status(x.name) == TaskStatus_e.HALTED)
            case x:
                assert(False), x
