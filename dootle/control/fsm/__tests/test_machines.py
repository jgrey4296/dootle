#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest
import doot
from dootle.control.fsm import machines as tm
from doot.enums import TaskStatus_e

logging = logmod.root

##-- basic model

class SimpleModel:
    name       = "blah"
    disabled   = False
    time_out   = 5

    def spec_missing(self, registry):
        return self.name not in registry

    def should_disable(self) -> bool:
        return self.disabled

    def should_wait(self, tracker) -> bool:
        match self.time_out:
            case x if 0 < x:
                self.time_out -= 1
                return False
            case _:
                return True

    def should_cancel(self) -> bool:
        return self.time_out < 0

    def should_skip(self) -> bool:
        return False

    def should_halt(self) -> bool:
        return False

    def should_fail(self) -> bool:
        return False

##-- end basic model

class TestTaskStateMachine:

    @pytest.fixture(scope="function")
    def fsm(self):
        return tm.TaskTrackMachine(SimpleModel())

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
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)


    def test_run_wait_timeout(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)


    def test_run_wait_proceed(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)


    def test_run_skip(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)


    def test_run_halt(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)


    def test_run_fail(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, registry={"blah":5})
        assert(fsm.fsm.state is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.fsm.state is TaskStatus_e.SUCCESS)

    def test_cond(self, fsm):
        fsm(registry={"blah":5}, tracker={"wait":False})
        assert(fsm.current_state_value is TaskStatus_e.DEAD)

    @pytest.mark.skip
    def test_todo(self):
        pass
