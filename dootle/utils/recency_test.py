#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

from __future__ import annotations

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

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import doot
import doot.errors
from doot.structs import DKeyed
from doot.enums import ActionResponse_e as ActE

TODAY                       = datetime.datetime.now().date()

@DKeyed.paths("target")
def recency_test(spec, state, target):
    """ skip rest of task if the target was modified today """
    if not target.exists():
        return

    mod_date = datetime.datetime.fromtimestamp(target.stat().st_mtime).date()
    if TODAY <= mod_date:
        # TODO print message informing of the skip
        return ActE.SKIP


@DKeyed.paths("source", "dest")
@DKeyed.types("tolerance", check=int, fallback=10_000_000)
def stale_test(spec, state, source, dest, tolerance):
    """
      Test two locations by their mod time.
      if the soure is older, or within tolerance
      skip rest of action group

    """
    # ExFat FS has lower resolution timestamps
    # So guard by having a tolerance:
    source_ns       = source.stat().st_mtime_ns
    match dest.exists():
        case True:
            dest_ns  = dest.stat().st_mtime_ns
        case False:
            dest_ns = 1
    source_newer    = source_ns > dest_ns
    difference      = int(max(source_ns, dest_ns) - min(source_ns, dest_ns))
    below_tolerance = difference <= tolerance

    printer.info("Source Newer: %s, below tolerance: %s", source_newer, below_tolerance)
    if (not source_newer) or below_tolerance:
        return ActE.SKIP
