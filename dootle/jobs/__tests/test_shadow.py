#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings
# ##-- stdlib imports

import pytest
import doot

doot._test_setup()

import dootle.jobs.shadow as JS

# Logging:
logging = logmod.root

# Type Aliases:

# Vars:

# Body:
class TestShadowing:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133
