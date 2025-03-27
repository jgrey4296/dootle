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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors
from doot.actions.core.action import DootBaseAction
from doot.mixins.path_manip import Walker_m
from doot.structs import TaskName, TaskSpec
from jgdv.structs.strang import CodeReference

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
