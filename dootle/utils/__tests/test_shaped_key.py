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
import doot
doot._test_setup()
from doot.structs import DKey
from dootle.utils.shaped_key import NPShapeDKey

logging = logmod.root

@pytest.mark.xfail
class TestNPShapeDKEy:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_sanity(self):
        arr = np.ones(5)
        assert(isinstance(arr, np.ndarray))

    def test_basic_construction(self):
        key = DKey("test", mark=np.ndarray, implicit=True, shape="blah")
        assert(isinstance(key, NPShapeDKey))


    def test_not_shape_key(self):
        key = DKey("test", implicit=True)
        assert(not isinstance(key, NPShapeDKey))


    def test_basic_expansion(self):
        key   = DKey("arr", mark=np.ndarray, implicit=True, shape="blah")
        state = {"arr": np.ones(5)}
        result = key.expand(state)
        assert(isinstance(result, np.ndarray))


    def test_expansion_fallback(self):
        key   = DKey("arr", fallback=np.zeros(5), mark=np.ndarray, implicit=True, shape="blah")
        result = key.expand({})
        assert(isinstance(result, np.ndarray))
        assert(result.sum() == 0)


    def test_expansion_no_fallabck(self):
        key   = DKey("arr", mark=np.ndarray, implicit=True, shape="blah")
        result = key.expand({})
        assert(result is None)
