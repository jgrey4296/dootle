#!/usr/bin/env python3
"""

"""

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
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from statemachine import State, StateMachine
from statemachine.states import States

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.enums import TaskStatus_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end loggingw

class TaskTrackMachine(StateMachine):
    """
      A Statemachine controlling the tracking of task states
    """
    # States
    _ = States.from_enum(TaskStatus_e,
                         initial=TaskStatus_e.NAMED,
                         final=TaskStatus_e.DEAD,
                         use_enum_instance=True)

    # Events
    setup = (
        _.NAMED.to(_.DEAD, cond='check_for_spec')
        | _.NAMED.to(_.DECLARED)
        | _.DECLARED.to(_.DEFINED)
        | _.DEFINED.to(_.INIT)
        | _.INIT.to.itself(internal=True)
        )

    run = (
        _.INIT.to(_.WAIT)
        | _.WAIT.to.itself(cond="should_wait", internal=True)
        | _.WAIT.to(_.READY)
        | _.READY.to(_.RUNNING)
        | _.RUNNING.to(_.SKIPPED, cond="should_skip")
        | _.RUNNING.to(_.HALTED,  cond="should_halt")
        | _.RUNNING.to(_.FAILED,  cond="should_fail")
        | _.RUNNING.to(_.SUCCESS)
        )

    disable  = _.DISABLED.from_(_.READY, _.WAIT, _.INIT, _.DECLARED, _.DEFINED, _.NAMED)
    skip     = _.SKIPPED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    fail     = _.FAILED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    halt     = _.HALTED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    succeed  = _.RUNNING.to(_.SUCCESS)

    complete = (
        _.TEARDOWN.from_(_.SUCCESS, _.FAILED, _.HALTED, _.SKIPPED, _.DISABLED)
        | _.TEARDOWN.to(_.DEAD)
        )

    # Composite Events
    progress = (setup | run | disable | skip | fail | halt | succeed | complete)

    # Listeners

    def __call__(self) -> Any:
        pass

    def check_for_spec(self) -> bool:
        return False

    def should_wait(self) -> bool:
        pass

    def should_skip(self) -> bool:
        pass

    def should_halt(self) -> bool:
        pass

    def should_fail(self) -> bool:
        pass

class ArtifactMachine(StateMachine):
    """
      A statemachine of artifact
    """
    # State
    Declared     = State(initial=True)
    Stale        = State()
    ToClean      = State()
    Removed      = State()
    Exists       = State()
    Finished     = State(final=True)

    progress     = (
        Declared.to(Stale, cond="is_stale")
        | Declared.to(ToClean, cond="should_clean")
        | Declared.to(Exists, cond="does_exists")
        | Declared.to(Finished)
        | Stale.to(Removed)
        | ToClean.to(Removed)
        | Removed.to(Declared)
        | Exists.to(Finished)
    )

    def __call__(self) -> Any:
        pass

    def is_stale(self) -> bool:
        pass

    def should_clean(self) -> bool:
        pass

    def does_exist(self) -> bool:
        pass

class TaskExecutionMachine(StateMachine):
    """
      Manaages the state progression of a running task
    """
    # State
    Ready      = State(initial=True)
    Finished   = State(final=True)
    Check      = State()
    Setup      = State()
    Body       = State()
    Action     = State()
    Relation   = State()
    Report     = State()
    Failed     = State()
    Successors = State()

    # Events
    run = (Ready.to(Check)
           | Check.to(Setup)
           | Setup.to(Body)
           | Body.to(Report, cond="no_actions_remain")
           | Report.to(Successors)
           | Successors.to(Finished)
           )
    action = (Body.to(Action, Relation, cond="actions_remain")
              | Action.to(Body)
              | Relation.to(Body)
              )
    fail   = (Failed.from_(Check, Setup, Body, Action, Relation, Report)
              | Failed.to(Successors)
              )

    # Composite Events
    progress = (action | run | fail)

    def __call__(self) -> Any:
        pass

    def actions_remain(self) -> bool:
        pass

    def no_actions_remain(self) -> bool:
        pass
