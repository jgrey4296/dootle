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
import os
import pathlib as pl
import warnings
from dataclasses import fields
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

logging = logmod.root

# ##-- 3rd party imports
import doot
import pytest

# ##-- end 3rd party imports

doot._test_setup()

# ##-- 3rd party imports
import doot._abstract
import doot.structs
from doot.actions.base_action import DootBaseAction
from doot.task.base_task import DootTask

# ##-- end 3rd party imports

class TestShellAction:

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = DootBaseAction()
        state  = { "count" : 0  }
        spec   = mocker.Mock(spec=doot.structs.ActionSpec)
        spec.args = []
        result = action(spec, state)
        assert(result['count'] == 1)
        assert("Base Action Called: 0" in caplog.messages)
