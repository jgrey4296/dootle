#!/usr/bin/env python3
"""

"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from importlib.metadata import EntryPoint

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.control.tracker._interface import WorkflowTracker_p
    from statemachine import State

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
MAX_LOOP        : Final[int]         = 100
SETUP_GROUP     : Final[str]         = "setup"
ACTION_GROUP    : Final[str]         = "actions"
FAIL_GROUP      : Final[str]         = "on_fail"
DEPENDS_GROUP   : Final[str]         = "depends_on"
CLEANUP_GROUP   : Final[str]         = "cleanup"

TASK_EP         : Final[EntryPoint]  = EntryPoint("task", group="doot.aliases.task", value="dootle.control.fsm.task:FSMTask")
ALIASES_UPDATE  : Final[dict]        = {
    "task" : [TASK_EP],
}
# Body:

@runtime_checkable
class TaskModel_Conditions_p(Protocol):
    """ The conditions a TaskTrackFSM calls """

    def spec_missing(self, *, tracker:WorkflowTracker_p) -> bool: ...

    def should_disable(self, source:State, *, tracker:WorkflowTracker_p) -> bool: ...

    def should_wait(self, *, tracker:WorkflowTracker_p) -> bool: ...

    def should_timeout(self) -> bool: ...

    def should_skip(self) -> bool: ...

    def should_halt(self) -> bool: ...

    def should_fail(self) -> bool: ...

    def state_is_needed(self, *, tracker:WorkflowTracker_p) -> bool: ...

@runtime_checkable
class TaskModel_Callbacks_p(Protocol):
    """
    Describes the callbacks for the FSM of a task
    """

    def on_enter_INIT(self, *, tracker:WorkflowTracker_p) -> None: ...  # noqa: N802

    def on_enter_RUNNING(self, *, step:int, tracker:WorkflowTracker_p) -> None: ...  # noqa: N802

    def on_enter_HALTED(self, *, tracker:WorkflowTracker_p) -> None: ...  # noqa: N802

    def on_enter_FAILED(self, *, tracker:WorkflowTracker_p) -> None: ...  # noqa: N802

    def on_exit_TEARDOWN(self) -> None: ...  # noqa: N802

class TaskModel_p(TaskModel_Callbacks_p, TaskModel_Conditions_p, Protocol):
    """
    Combines the TaskModel Conditions and Callbacks protocols
    """
    pass

@runtime_checkable
class ArtifactModel_p(Protocol):
    """ Describes the callbacks for an FSM of a task """

    def is_stale(self) -> bool: ...

    def should_clean(self) -> bool: ...

    def does_exist(self) -> bool: ...
