#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer = logmod.getLogger("doot._printer")

import numpy as np
import doot
import doot.errors
from doot.structs import DootKey

SEED = DootKey.make("seed")
RNG  = DootKey.make("_rng")
NUM  = DootKey.make("num")

@DootKey.kwrap.types("seed", hint={"on_fail":None})
@DootKey.kwrap.returns("_rng")
def new_random(spec, state, seed):
    rng = np.random.default_rng(seed=seed)
    return { "_rng" : rng }

@DootKey.kwrap.types("_rng")
@DootKey.kwrap.types("num")
def integers(spec, state, _rng, num):
    result = _rng.integers(0, 10, num)
    printer.info("Got: %s", result)
