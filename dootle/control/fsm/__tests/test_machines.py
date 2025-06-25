#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="no-any-return"
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
from doot.workflow import TaskArtifact
# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.control.fsm import machines as tm

# ##-- end 1st party imports

from doot.workflow import TaskSpec
from ..task import FSMTask
from .. import _interface as API # noqa: N812

logging = logmod.root

##-- basic model

class SimpleTaskModel:
    """ A Simple task model

    Just for checking the FSM.
    Provides the required conditions for the FSM
    """

    def __init__(self):
        self.name      = "blah"
        self.disabled  = False
        self.time_out  = -1
        self.skip      = False
        self.halt      = False
        self.fail      = False
        self.data      = {'has_run': False}
        self.status    = None

    def spec_missing(self, *, tracker):
        return self.name not in tracker

    def should_disable(self) -> bool:
        return self.disabled

    def should_wait(self, *, tracker) -> bool:
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

    def on_enter_RUNNING(self):
        self.data['has_run'] = True

class SimpleArtifactModel:

    def __init__(self):
        self.state   = None
        self.stale   = False
        self.clean   = False
        self.exists  = False

    def is_stale(self) -> bool:
        return self.stale

    def should_clean(self) -> bool:
        return self.clean

    def does_exist(self) -> bool:
        return self.exists

class SimpleMainModel:

    def should_fail(self) -> bool:
        return False

class SimpleOverlordModel:
    pass
##-- end basic model

class TestSimpleTaskModel:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_fulfills_conditions(self):
        assert(isinstance(SimpleTaskModel, API.TaskModel_Conditions_p))

    @pytest.mark.xfail
    def test_fullfills_callbacks(self):
        assert(isinstance(SimpleTaskModel, API.TaskModel_Callbacks_p))

class TestTaskMachine:
    """ Test a basic task model as a task FSM machine runs,
    by event
    """

    @pytest.fixture(scope="function")
    def fsm(self):
        task = SimpleTaskModel()
        return tm.TaskMachine(task)

    @pytest.fixture(scope="function")
    def task(self):
        spec = TaskSpec.build({"name":"simple::basic"})
        task = FSMTask(spec)
        return task

    def test_sanity(self, fsm):
        assert(True is True)
        assert(fsm.current_state_value is TaskStatus_e.NAMED)

    def test_start(self, fsm):
        """
        The FSM starts just named
        """
        assert(fsm.current_state.value is TaskStatus_e.NAMED)

    def test_build_with_actual_task(self, task):
        """
        The FSM starts just named
        """
        assert(task.spec_missing)
        fsm = tm.TaskMachine(task)

    ##--| setup

    def test_setup(self, fsm):
        """ Setting up takes the task from named to init """
        assert(fsm.current_state.value is TaskStatus_e.NAMED)
        fsm.setup(tracker={"blah":5})
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
        fsm.setup(tracker={})
        assert(fsm.current_state_value is TaskStatus_e.DEAD)

    def test_setup_should_disable(self, fsm):
        """
        Setting up a disabled task result in it being disabled
        """
        fsm.model.disabled = True
        assert(fsm.current_state_value is TaskStatus_e.NAMED)
        fsm.setup(tracker={"blah":5})
        fsm.setup()
        fsm.setup()
        assert(fsm.current_state_value is TaskStatus_e.DISABLED)

    ##--| run

    def test_run(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.status is TaskStatus_e.SUCCESS)
        assert(fsm.model.data['has_run'] is True)

    def test_run_wait_timeout(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm.model.time_out = 5
        assert(fsm.model.data['has_run'] is False)
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.status is TaskStatus_e.TEARDOWN)
        assert(fsm.model.data['has_run'] is False)

    def test_run_wait_proceed(self, fsm):
        """
        Normally a running task progresses to success

        """
        fsm.model.time_out = 5
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.WAIT)
        assert(fsm.model.status is TaskStatus_e.WAIT)
        fsm.model.time_out = -1
        fsm(tracker={"blah":5}, until=TaskStatus_e.SUCCESS)
        assert(fsm.model.status is TaskStatus_e.SUCCESS)
        assert(fsm.model.data['has_run'] is True)

    def test_run_skip(self, fsm):
        """
        Checks the skip path

        """
        fsm.model.skip = True
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.status is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.SKIPPED])
        assert(fsm.model.status is TaskStatus_e.SKIPPED)
        assert(fsm.model.data['has_run'] is False)

    def test_run_halt(self, fsm):
        """
        Checks the halt path
        """
        fsm.model.halt = True
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.status is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.HALTED])
        assert(fsm.model.status is TaskStatus_e.HALTED)
        assert(fsm.model.data['has_run'] is True)

    def test_run_fail(self, fsm):
        """
        checks the fail path
        """
        fsm.model.fail = True
        fsm(until=TaskStatus_e.INIT, tracker={"blah":5})
        assert(fsm.model.status is TaskStatus_e.INIT)
        fsm(tracker={"blah":5}, until=TaskStatus_e.READY)
        assert(fsm.model.status is TaskStatus_e.READY)
        fsm(until=[TaskStatus_e.FAILED])
        assert(fsm.model.status is TaskStatus_e.FAILED)
        assert(fsm.model.data['has_run'] is True)

    ##--| finish

    def test_finish(self, fsm):
        pass

class TestArtifactMachine:

    @pytest.fixture(scope="function")
    def fsm(self):
        return tm.ArtifactMachine()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestMainMachine:

    @pytest.fixture(scope="function")
    def fsm(self):
        return tm.MainMachine()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestOverlordMachine:

    @pytest.fixture(scope="function")
    def fsm(self):
        return tm.OverlordMachine()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

@pytest.mark.skip
class TestMachine_Dot:
    """ Write out the dot graphs of the machines """

    @pytest.fixture(scope="function")
    def fsm(self):
        task = SimpleTaskModel()
        return tm.TaskMachine(task)

    @pytest.fixture(scope="function")
    def target(self):
        return pl.Path(__file__).parent.parent  / "_graphs"

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_task_dot(self, fsm, target):
        fsm_name  = type(fsm).__name__
        text      = fsm._graph().to_string()
        tfile     = target / f"_{fsm_name}.dot"
        tfile.write_text(text)
        assert(tfile.exists())

    def test_artifact_dot(self, target):
        loc       = SimpleArtifactModel()
        fsm       = tm.ArtifactMachine(loc)
        fsm_name  = type(fsm).__name__
        text      = fsm._graph().to_string()
        tfile     = target / f"_{fsm_name}.dot"
        tfile.write_text(text)
        assert(tfile.exists())

    def test_main_dot(self, target):
        fsm       = tm.MainMachine(SimpleMainModel())
        fsm_name  = type(fsm).__name__
        text      = fsm._graph().to_string()
        tfile     = target / f"_{fsm_name}.dot"
        tfile.write_text(text)
        assert(tfile.exists())


    def test_overlord_dot(self, target):
        fsm       = tm.OverlordMachine(SimpleOverlordModel())
        fsm_name  = type(fsm).__name__
        text      = fsm._graph().to_string()
        tfile     = target /  f"_{fsm_name}.dot"
        tfile.write_text(text)
        assert(tfile.exists())
