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
import random
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
from doot.actions.base_action import DootBaseAction
from doot.mixins.path_manip import Walker_m
from doot.structs import DKey, DKeyed, TaskName, TaskSpec
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class JobLimitAction(DootBaseAction):
    """
      Limits a list to an amount, *overwriting* the 'from' key,

    count: int. (-1 = no-op)
    method: random.sample or Coderef([spec, state, list[taskspec]] -> list[taskspec])

    registered as: job.limit
    """

    @DKeyed.types("count")
    @DKeyed.references("method")
    @DKeyed.redirects("from_")
    def __call__(self, spec, state, count, method, _update):
        if count == -1:
            return

        _from = _update.expand(spec, state)
        match method:
            case None:
                limited = random.sample(_from, count)
            case CodeReference():
                fn      = method()
                limited = fn(spec, state, _from)

        return { _update : limited }
