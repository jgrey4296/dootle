#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TaskPolicyEnum(enum.Flag):
    """
      Combinable Policy Types:
      breaker  : fails fast
      bulkhead : limits extent of problem and continues
      retry    : trys to do the action again to see if its resolved
      timeout  : waits then fails
      cache    : reuses old results
      fallback : uses defined alternatives
      cleanup  : uses defined cleanup actions
      debug    : triggers pdb
      pretend  : pretend everything went fine
      accept   : accept the failure

      breaker will overrule bulkhead
    """
    BREAKER  = enum.auto()
    BULKHEAD = enum.auto()
    RETRY    = enum.auto()
    TIMEOUT  = enum.auto()
    CACHE    = enum.auto()
    FALLBACK = enum.auto()
    CLEANUP  = enum.auto()
    DEBUG    = enum.auto()
    PRETEND  = enum.auto()
    ACCEPT   = enum.auto()
