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
from secrets import randbits
# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKeyed
import doot
import doot.errors
import numpy as np

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

RNG_STATE_S : Final[str] = "__rng"
##--|
@DKeyed.types("seed", check=int|None, fallback=None)
@DKeyed.paths("seed_path", check=pl.Path|None, fallback=None)
@DKeyed.returns(RNG_STATE_S, check=np.random.Generator)
def rng_fresh(spec, state, seed, seed_path):
    """ Create a new (maybe seeded) random number generator,
    added to state._rng

    Uses PCG-64 bitgenerator by default
    With no seed, uses secrets.randbits(128)
    """
    if seed and seed_path and seed_path.exists():
        raise doot.errors.ActionError("Tried to use a seed and seed stored in a path")

    if seed_path:
        raise NotImplementedError("loading a seed from a file isn't implemented yet")

    if not seed:
        seed = randbits(128)
        seed_sequence = np.random.SeedSequence(seed)
        bitgen        = np.random.PCG64(seed_sequence)
        rng           = np.random.Generator(bitgen)
    return { RNG_STATE_S : rng }

@DKeyed.types(RNG_STATE_S, check=np.random.Generator)
@DKeyed.types("num", check=int|None, fallback=5)
@DKeyed.redirects("update_")
def rng_spawn(spec, state, _rng, num, _update):
    """ Spawn independent sub rngs (for passing to job children?) """
    children = _rng.spawn(num)
    return { _update : children }

@DKeyed.types(RNG_STATE_S, check=np.random.Generator)
@DKeyed.types("count", "min", "max", check=int|None)
@DKeyed.redirects("update_")
def rng_ints(spec, state, _rng, count, _min, _max, _update):
    """ Use the rng to get a count of integers from min to max """
    result = _rng.integers(_min or 0, _max or 10, num or 10)
    doot.report.trace("Got: %s", result)

    return { _update : result }

@DKeyed.types(RNG_STATE_S, check=np.random.Generator)
@DKeyed.formats("dist", fallback="integers")
@DKeyed.types("shape", check=int|list|None)
@DKeyed.args
@DKeyed.redirects("update_")
def rng_draw(spec, state, _rng, dist, shape, args, _update):
    """ Use the rng to get a count of integers from min to max """
    result = None
    if not hasattr(_rng, dist):
        raise doot.errors.ActionError(f"RNG Distribution not found: {dist}")

    gen = getattr(_rng, dist)
    result = gen(*args, size=shape)
    assert(result is not None)
    doot.report.detail("Generated Random (%s): %s", dist, result)
    return { _update : result }

@DKeyed.types(RNG_STATE_S, check=np.random.Generator)
@DKeyed.types("base")
@DKeyed.formats("form")
@DKeyed.redirects("update_")
def rng_shuffle(spec, state, _rng, base, form, _update):
    """ For shuffling and permuting a state value """
    raise NotImplementedError("rng shuffling is not implemented")
