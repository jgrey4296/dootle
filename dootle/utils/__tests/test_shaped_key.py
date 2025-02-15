#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import numpy as np
from jgdv.structs.dkey import DKey
import doot
doot._test_setup()
from dootle.utils.shaped_key import NPShapeDKey

logging = logmod.root

class TestNPShapeDKEy:

    def test_sanity(self):
        arr = np.ones(5)
        assert(isinstance(arr, np.ndarray))

    def test_basic_construction(self):
        key = DKey("test", mark="np", implicit=True)
        assert(isinstance(key, NPShapeDKey))


    def test_fail_on_no_shape(self):
        with pytest.raises(TypeError):
            key = DKey("test", mark="np", implicit=True, shape="blah")

    def test_not_shape_key(self):
        key = DKey("test", implicit=True)
        assert(not isinstance(key, NPShapeDKey))

    def test_basic_expansion(self):
        key   = DKey("arr", mark="np", implicit=True, shape=(5,))
        state = {"arr": np.ones(5)}
        match key.expand(state):
            case np.ndarray() as x:
                assert(True)
            case x:
                 assert(False), x

    def test_expansion_fallback(self):
        key   = DKey("arr", fallback=np.zeros(5), mark="np", implicit=True, shape=(5,))
        match key.expand({}):
            case np.ndarray() as x:
                assert(x.sum() == 0)
            case x:
                 assert(False), x

    def test_expansion_no_fallback(self):
        key   = DKey("arr", mark="np", implicit=True, shape=(5,))
        match key.expand({}):
            case None:
                assert(True)
            case x:
                 assert(False), x
