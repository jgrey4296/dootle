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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from statemachine import State, StateMachine
from statemachine.states import States

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import TaskStatus_e

from . import _interface as API
# ##-- end 1st party imports

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

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
    # Setup: named -> init | dead
    setup = (
        _.NAMED.to(_.DEAD, cond='spec_missing')
        | _.NAMED.to(_.DECLARED)
        | _.DECLARED.to(_.DEFINED)
        | _.DEFINED.to(_.DISABLED, cond="should_disable")
        | _.DEFINED.to(_.INIT)
        )

    # Run: init -> success | failed | halted | skipped
    run = (
        _.INIT.to(_.WAIT)
        | _.WAIT.to.itself(cond="should_wait", internal=True)
        | _.WAIT.to(_.FAILED,   cond="should_cancel")
        | _.WAIT.to(_.READY)
        | _.READY.to(_.SKIPPED, cond="should_skip")
        | _.READY.to(_.RUNNING)
        | _.RUNNING.to(_.HALTED,  cond="should_halt")
        | _.RUNNING.to(_.FAILED,  cond="should_fail")
        | _.RUNNING.to(_.SUCCESS)
        )

    # Finish: success | failed | halted | skipped -> dead
    finish   = (
        _.TEARDOWN.from_(_.SUCCESS, _.FAILED, _.HALTED, _.SKIPPED, _.DISABLED)
        | _.TEARDOWN.to(_.DEAD)
        )

    # Utility events
    disable  = _.DISABLED.from_(_.READY, _.WAIT, _.INIT, _.DECLARED, _.DEFINED, _.NAMED)
    skip     = _.SKIPPED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    halt     = _.HALTED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)
    fail     = _.FAILED.from_(_.READY, _.RUNNING, _.WAIT, _.INIT, _.DECLARED, _.DEFINED)

    # Composite Events
    progress = (setup | run | disable | skip | fail | halt | finish )

    def __init__(self, task:API.TaskModel_p):
        super().__init__(task)

    def __call__(self, *, until:Maybe[TaskStatus_e|list[TaskStatus_e]]=None, **kwargs) -> Any:
        base_states = [TaskStatus_e.DEAD]
        match until:
            case None | []:
                pass
            case TaskStatus_e() as x:
                base_states.append(x)
            case [*xs]:
                base_states += xs

        while self.current_state_value not in base_states:
            try:
                self.progress(**kwargs)
            except doot.errors.DootError as err:
                self.fail()
        else:
            return self.current_state_value

    def after_transition(self, event, state):
        logging.info("%s : %s", event, state)

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

    def __init__(self, artifact:API.ArtifactModel_p):
        super().__init__(artifact)




class DootMainMachine(StateMachine):
    """
    For running doot as main
    """
    
    # States
    init      = State(initial=True)
    setup     = State()
    plugins   = State()
    cli       = State()
    reporter  = State()
    commands  = State()
    tasks     = State()
    run       = State()
    fail      = State()
    report    = State()
    shutdown  = State()
    finished  = State(final=True)

    # Events

class DootOverlordMachine(StateMachine):

    init        = State(initial=True)
    constants   = State()
    config_file = State()
    logging     = State()
    locations   = State()
    global      = State()
    ready       = State(final=True)
