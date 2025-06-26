#!/usr/bin/env python3
"""
TEST File updated

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202, B011, ERA001

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
# ##-- end 3rd party imports


##--|
from ..fsm_tracker import FSMTracker
from ..runner import FSMRunner
from ..task import FSMTask
from ..machines import TaskMachine
from doot.util.factory import TaskFactory
from doot.workflow import TaskSpec
from doot.workflow._interface import TaskStatus_e
##--|

# ##-- types
# isort: off
# General
import abc
import collections.abc
import typing
import types
from typing import cast, assert_type, assert_never
from typing import Generic, NewType, Never
from typing import no_type_check, final, override, overload
# Protocols and Interfaces:
from typing import Protocol, runtime_checkable
if typing.TYPE_CHECKING:
    from typing import Final, ClassVar, Any, Self
    from typing import Literal, LiteralString
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
factory = TaskFactory()
# Body:
class TestFSMRunner:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        tracker = FSMTracker()
        match FSMRunner(tracker=tracker):
            case FSMRunner():
                assert(True)
            case x:
                assert(False), x


    def test_simple_run(self, mocker):
        spec                         = factory.build({"name":"simple::basic"})
        tracker                      = FSMTracker()
        tracker.register(spec)
        tracker.build()
        runner                       = FSMRunner(tracker=tracker)
        runner.run_next_task()

    ##--|
    @pytest.mark.skip
    def test_todo(self):
        pass
