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

from dootle.actions.shell import DootShellAction

class TestShellAction:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = DootShellAction()
        spec = doot.structs.ActionSpec.build({"do":"shell", 
                                              "args":["ls"],
                                              "update_":"blah",
                                              })
        state  = { "count" : 0  }
        match action(spec, state):
            case {"blah": str()}:
                assert(True)
            case x:
                 assert(False), x


    def test_call_action_split_lines(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = DootShellAction()
        spec = doot.structs.ActionSpec.build({"do":"shell", 
                                              "args":["ls", "-l"],
                                              "update_":"blah",
                                              })
        state  = { "count" : 0, "splitlines":True}
        match action(spec, state):
            case {"blah": list()}:
                assert(True)
            case x:
                 assert(False), x


    def test_call_action_fail(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = DootShellAction()
        spec = doot.structs.ActionSpec.build({"do":"shell", 
                                              "args":["awgg"],
                                              "update_":"blah",
                                              })
        state  = { "count" : 0, "splitlines":True}
        match action(spec, state):
            case False:
                assert(True)
            case x:
                 assert(False), x
        


class TestShellBaking:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestShellInteractive:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133
