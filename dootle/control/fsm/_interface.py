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

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
MAX_LOOP  : Final[int]     = 100
# Body:

class TaskModel_p(Protocol):

    def spec_missing(self, tracker): ...

    def should_disable(self) -> bool: ...

    def should_wait(self, tracker) -> bool: ...

    def should_cancel(self) -> bool: ...

    def should_skip(self) -> bool: ...

    def should_halt(self) -> bool: ...

    def should_fail(self) -> bool: ...

    def on_enter_running(self, step:int) -> None: ...

    def on_enter_failed(self) -> None: ...

    def on_enter_init(self) -> None: ...
    def on_enter_teardown(self) -> None: ...

class ArtifactModel_p(Protocol):

    def is_stale(self) -> bool: ...

    def should_clean(self) -> bool: ...

    def does_exist(self) -> bool: ...
