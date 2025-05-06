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
from jgdv.debugging import SignalHandler, NullHandler
from doot.control.runner import DootRunner
# ##-- end 3rd party imports

from .task import FSMTask

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow import RelationSpec, ActionSpec, TaskArtifact, TaskName, TaskSpec
from doot.workflow._interface import ActionResponse_e as ActRE

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
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
from doot.workflow._interface import (Action_p, Job_p, Task_p)
from doot.control.runner._interface import TaskRunner_p
from doot.control.tracker._interface import TaskTracker_p

from typing import ContextManager
# isort: on
# ##-- end types

##-- logging
logging           = logmod.getLogger(__name__)
##-- end logging

##--| Vars
skip_msg                   : Final[str] = doot.constants.printer.skip_by_condition_msg
max_steps                  : Final[int] = doot.config.on_fail(100_000).settings.tasks.max_steps()

SETUP_GROUP                : Final[str] = "setup"
ACTION_GROUP               : Final[str] = "actions"
FAIL_GROUP                 : Final[str] = "on_fail"
DEPENDS_GROUP              : Final[str] = "depends_on"

##--|

@Proto(TaskRunner_p, check=False)
class FSMRunner(DootRunner):
    """ Doot Runner which accepts FSM wrapped Tasks/Jobs/Artifacts """

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
                case FSMTask():
                    self._run_fsm(task)
                case TaskArtifact():
                    self._notify_artifact(task)
                case Job_p():
                    self._expand_job(task)
                case Task_p():
                    self._execute_task(task)
                case x:
                    doot.report.error("Unknown Value provided to runner: %s", x)
        except doot.errors.TaskError as err:
            err.task = task
            self._handle_failure(err)
        except doot.errors.DootError as err:
            self._handle_failure(err)
        except Exception as err:
            doot.report.fail()
            self.tracker.clear_queue()
            raise
        else:
            self._handle_task_success(task)
            self._sleep(task)
            self.step += 1

    def _run_fsm(self, fsm:FSMTask) -> None:
        # Execute the fsm, possibly add additional tasks to the tracker
        fsm(step=self.step, tracker=self.tracker)
