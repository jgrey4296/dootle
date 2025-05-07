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

from jgdv import Proto, Mixin
from doot.reporters import _interface as API  # noqa: N812
from doot.reporters import BasicReporter, TraceFormatter

from . import _interface as LAPI

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

    type Logger = logmod.Logger
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

@Proto(API.Reporter_i)
class FancyReporter(BasicReporter):
    """ An alternative reporter.


    Activated by setting doot.toml:
    settings.commands.run.reporter = 'dootle.reporter:FancyReporter'
    """

    def __init__(self, *args:Any, logger:Maybe[Logger]=None, segments:Maybe[dict]=None, **kwargs:Any) -> None:
        super().__init__(*args,
                         logger=logger,
                         segments=segments or LAPI.FANCY_SEGMENTS,
                         **kwargs)
