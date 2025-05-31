#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import pytest
from doot.workflow._interface import TaskStatus_e

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.control.fsm import machines as tm

# ##-- end 1st party imports

logging = logmod.root

##-- basic model

class SimpleTaskModel:
    """ A Simple task model

    Just for checking the FSM.
    Provides the required conditions for the FSM
    """

    def __init__(self):
        self.name       = "blah"
        self.disabled   = False
        self.time_out   = -1
        self.skip       = False
        self.halt       = False
        self.fail       = False
        self.data       = {'has_run': False}

    def spec_missing(self, registry):
        return self.name not in registry

    def should_disable(self) -> bool:
        return self.disabled

    def should_wait(self, tracker) -> bool:
        match self.time_out:
            case x if 0 < x:
                self.time_out -= 1
                return True
            case _:
                return False

    def should_cancel(self) -> bool:
        return 0 <= self.time_out < 1

    def should_skip(self) -> bool:
        return self.skip

    def should_halt(self) -> bool:
        return self.halt

    def should_fail(self) -> bool:
        return self.fail

    @tm.TaskTrackMachine._.RUNNING.enter
    def _run(self):
        self.data['has_run'] = True

##-- end basic model

class TestTaskStateMachine:

    @pytest.fixture(scope="function")
    def fsm(self):
        return tm.TaskTrackMachine(SimpleTaskModel())

    def test_sanity(self, fsm):
        assert(True is True)
        assert(fsm.current_state_value is TaskStatus_e.NAMED)

    def test_start(self, fsm):
        """
        The FSM starts just named
        """
        assert(fsm.current_state.value is TaskStatus_e.NAMED)

    def test_setup(self, fsm):
        """ Setting up takes the task from named to init """
        assert(fsm.current_state.value is TaskStatus_e.NAMED)
        fsm.setup(registry={"blah":5})
        assert(fsm.current_state.value is TaskStatus_e.DECLARED)
        fsm.setup()
        assert(fsm.current_state.value is TaskStatus_e.DEFINED)
        fsm.setup()
        assert(fsm.current_state.value is TaskStatus_e.INIT)

    def test_setup_spec_missing(self, fsm):
        """ The spec missing from the registry
        shortcuts to dead
        """
        assert(fsm.current_state_value is TaskStatus_e.NAMED)
        fsm.setup(registry={})
        assert(fsm.current_state_value is TaskStatus_e.DEAD)

    def test_setup_should_disable(self, fsm):
        """
        Setting up a disabled task result in it being disabled
        """
        fsm.model.disabled = True
        assert(fsm.current_state_value is TaskStatus_e.NAMED)
        fsm.setup(registry={"blah":5})
        fsm.setup()
        fsm.setup()
        assert(fsm.current_state_value is TaskStatus_e.DISABLED)

    def test_run(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.state is TaskStatus_e.SUCCESS)
        assert(fsm.model.data['has_run'] is True)

    def test_run_wait_timeout(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm.model.time_out = 5
        assert(fsm.model.data['has_run'] is False)
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.state is TaskStatus_e.DEAD)
        assert(fsm.model.data['has_run'] is False)

    def test_run_wait_proceed(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm.model.time_out = 5
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.WAIT)
        assert(fsm.model.state is TaskStatus_e.WAIT)
        fsm.model.time_out = -1
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.state is TaskStatus_e.SUCCESS)
        assert(fsm.model.data['has_run'] is True)

    def test_run_skip(self, fsm):
        """
        Checks the skip path

        """
        fsm.model.skip = True
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.state is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.SKIPPED])
        assert(fsm.model.state is TaskStatus_e.SKIPPED)
        assert(fsm.model.data['has_run'] is False)

    def test_run_halt(self, fsm):
        """
        Checks the halt path
        """
        fsm.model.halt = True
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.state is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.HALTED])
        assert(fsm.model.state is TaskStatus_e.HALTED)
        assert(fsm.model.data['has_run'] is True)

    def test_run_fail(self, fsm):
        """
        checks the fail path
        """
        fsm.model.fail = True
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.model.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.state is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.FAILED])
        assert(fsm.model.state is TaskStatus_e.FAILED)
        assert(fsm.model.data['has_run'] is True)

    @pytest.mark.skip
    def test_todo(self):
        pass
