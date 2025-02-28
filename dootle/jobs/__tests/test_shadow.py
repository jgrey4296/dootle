#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202

# Imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest
import doot


import dootle.jobs.shadow as JS

# Logging:
logging = logmod.root

# Type Aliases:

# Vars:

# Body:
class TestShadowing:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    
    
    @pytest.mark.skip 
    def test_todo(self):
        pass
