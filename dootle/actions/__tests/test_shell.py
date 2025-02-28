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

# ##-- 3rd party imports
import doot
import doot._abstract
import doot.structs
import pytest
import sh
from doot.actions.core.action import DootBaseAction
from doot.task.core.task import DootTask

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.actions.shell import ShellAction, ShellBake, ShellBakedRun

# ##-- end 1st party imports

logging = logmod.root

IMPORT_STR = "dootle.actions.shell:ShellAction"

class TestShellAction:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self):
        action = DootBaseAction()
        assert(isinstance(action, DootBaseAction))

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = ShellAction()
        spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
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
        action = ShellAction()
        spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
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
        action = ShellAction()
        spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
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

    def test_initial(self):
        match ShellBake():
            case ShellBake():
                assert(True)
            case x:
                 assert(False), x

    def test_call_action(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = ShellBake()
        spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                              "args":["ls"],
                                              "update_":"blah",
                                              })
        state  = { "count" : 0  }
        match action(spec, state):
            case {"blah": sh.Command() as x}:
                assert(True)
            case x:
                 assert(False), x

    def test_chain(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = ShellBake()
        spec1 = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                              "args":["ls"],
                                              "update_":"blah",
                                              })
        spec2 = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                               "args":["grep", "doot"],
                                               "in_":"blah",
                                               "update_":"bloo"
                                                })
        state  = { "count" : 0  }
        match action(spec1, state):
            case {"blah": sh.Command()} as result:
                assert(True)
            case x:
                 assert(False), x

        match action(spec2, result):
            case {"bloo": sh.Command()} as result:
                assert(True)
            case x:
                 assert(False), x

    def test_run_chain(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        bake_action = ShellBake()
        run_action = ShellBakedRun()
        spec1 = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                              "args":["ls"],
                                              "update_":"blah",
                                              })
        spec2 = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                               "args":["grep", "doot"],
                                               "in_":"blah",
                                               "update_":"bloo"
                                                })
        run_spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                                  "in_":"bloo",
                                                  "update_":"out"})
        state  = { "count" : 0  }
        c1 = bake_action(spec1, state)
        c2 = bake_action(spec2, c1)
        match run_action(run_spec, c2):
            case {"out": x}:
                assert(True)
            case x:
                 assert(False), x

    def test_call_action_fail(self, caplog, mocker):
        caplog.set_level(logmod.DEBUG, logger="_printer_")
        action = ShellBake()
        spec = doot.structs.ActionSpec.build({"do":IMPORT_STR,
                                              "args":["aweg"],
                                              "update_":"blah",
                                              })
        state  = { "count" : 0  }
        match action(spec, state):
            case False:
                assert(True)
            case x:
                 assert(False), x

@pytest.mark.skip
class TestShellInteractive:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133
