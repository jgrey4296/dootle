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

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Global Vars:

# Body:

class ArtifactMachine(StateMachine):
    """
      A statemachine of artifact
    """
    # State
    Declared    = State(initial=True)
    Stale       = State()
    ToClean     = State()
    Removed     = State()
    Exists      = State(final=True)

    progress = (
        Declared.to(Stale, cond=None)
        | Declared.to(ToClean, cond=None)
        | Declared.to(Exists)
        | Stale.to(Removed)
        | ToClean.to(Removed)
        | Removed.to(Declared)
    )
