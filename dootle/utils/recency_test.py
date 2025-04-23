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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKeyed
import doot
import doot.errors
from doot.enums import ActionResponse_e as ActE

# ##-- end 3rd party imports

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
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

    doot.report.trace("%s is Stale", source.name)
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
