#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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
import doot
import doot.errors
from doot.enums import ActionResponse_e as ActE
from doot.structs import DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging


TODAY                       = datetime.datetime.now().date()

@DKeyed.paths("target")
def recency_test(spec, state, target):
    """ skip rest of task if the target exists and was modified today """
    if not target.exists():
        return None

    mod_date = datetime.datetime.fromtimestamp(target.stat().st_mtime).date()
    if not (TODAY <= mod_date):
        return None

    printer.info("%s was modified today", target.name)
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
    match source.exists(), dest.exists():
        case False, _:
            return True
        case _, False:
            return True
        case True, True:
            pass

    source_ns       = source.stat().st_mtime_ns
    dest_ns         = dest.stat().st_mtime_ns
    source_newer    = source_ns > dest_ns
    difference      = int(max(source_ns, dest_ns) - min(source_ns, dest_ns))
    below_tolerance = difference <= tolerance

    printer.debug("Source Newer: %s, below tolerance: %s", source_newer, below_tolerance)
    if (not source_newer) or below_tolerance:
        printer.info("%s is Stale", source.name)
        return ActE.SKIP
