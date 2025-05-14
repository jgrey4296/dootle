#!/usr/bin/env python3
"""
TEST File updated

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202, B011

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
# ##-- end 3rd party imports

from doot.reporters import _interface as API  # noqa: N812

##--|
from .. import FancyReporter
##--|

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
L0_DEPTH : int       = 1
L1_DEPTH : int       = 2
L2_DEPTH : int       = 3
# Body:

class TestFancyReporter:
    @pytest.mark.skip
    def test_todo(self):
        pass

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        match FancyReporter():
            case API.Reporter_p():
                assert(True)
            case x:
                 assert(False), x

    def test_basic_trace(self, caplog):
        obj = FancyReporter()
        caplog.set_level(logmod.NOTSET, logger=obj.log.name)
        obj.root()
        obj.act("test", "blah")
        obj.finished()
        assert("┳" in caplog.text)
        assert("┼◇  [test]  : blah" in caplog.text)
        assert("┻" in caplog.text)

    def test_ctx_manager(self):
        obj                    = FancyReporter()
        assert(obj.state.depth == L0_DEPTH)
        with obj:
            assert(obj.state.depth == L1_DEPTH)

        assert(obj.state.depth == L0_DEPTH)

    def test_branch(self, caplog):
        obj = FancyReporter()
        caplog.set_level(logmod.NOTSET, logger=obj.log.name)
        with obj.branch("Test"):
            assert(obj.state.log_level > logmod.INFO)
            obj.act("Log", "blah")
            obj.result(["blah"])

        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Start] : Test" in caplog.text)
        assert("┊   ┼◇  [Log]   : blah" in caplog.text)
        assert("┢◀──╯   []      : blah" in caplog.text)


    def test_double_branch(self, caplog):
        obj = FancyReporter()
        assert(obj.state.depth == L0_DEPTH)
        obj.root()
        obj.branch("first")
        assert(obj.state.depth == L1_DEPTH)
        assert(obj.state.log_level > logmod.INFO)
        obj.act("Log", "act1")

        obj.branch("second")
        assert(obj.state.depth == L2_DEPTH)
        obj.act("Log", "act2")
        obj.act("Log", "act3")
        obj.result(["second"])

        assert(obj.state.depth == L1_DEPTH)
        obj.act("Log", "act4")
        obj.result(["first"])

        assert(obj.state.depth == L0_DEPTH)
        obj.finished()

        assert("┳" in caplog.text)
        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Start] : first" in caplog.text)
        assert("┊   ┼◇  [Log]   : act1" in caplog.text)
        assert("┊   ┣─▶─╮" in caplog.text)
        assert("┊   ┊   ▼   [Start] : second" in caplog.text)
        assert("┊   ┊   ┼◇  [Log]   : act2" in caplog.text)
        assert("┊   ┊   ┼◇  [Log]   : act3" in caplog.text)
        assert("┊   ┢◀──╯   []      : second" in caplog.text)
        assert("┊   ┼◇  [Log]   : act4" in caplog.text)
        assert("┢◀──╯   []      : first" in caplog.text)
        assert("┻" in caplog.text)



class TestFancyReporter_Tree:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_custom_tree(self, caplog):
        data = [
            "First",
            "Second",
            ("Third", ["a", "b", "c"]),
            ("Fourth", ["d", "e", "f"]),
            "Fifth",
        ]

        obj = FancyReporter()
        obj.tree(data)

        assert("┳" in caplog.text)
        assert("┼◇  [Leaf]  : First" in caplog.text)
        assert("┼◇  [Leaf]  : Second" in caplog.text)
        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Branch] : Third" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : a" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : b" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : c" in caplog.text)
        assert("┊   ┻" in caplog.text)
        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Branch] : Fourth" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : d" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : e" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : f" in caplog.text)
        assert("┊   ┻" in caplog.text)
        assert("┼◇  [Leaf]  : Fifth" in caplog.text)
        assert("┻" in caplog.text)


    def test_nested_tree(self, caplog):
        data = [
            "First",
            ("Middle", ["a", ("Nested", ["b", "c"]), "d"]),
            "Last",
        ]

        obj = FancyReporter()
        obj.tree(data)

        assert("┳" in caplog.text)
        assert("┼◇  [Leaf]  : First" in caplog.text)
        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Branch] : Middle" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : a" in caplog.text)
        assert("┊   ┣─▶─╮" in caplog.text)
        assert("┊   ┊   ▼   [Branch] : Nested" in caplog.text)
        assert("┊   ┊   ┼◇  [Leaf]  : b" in caplog.text)
        assert("┊   ┊   ┼◇  [Leaf]  : c" in caplog.text)
        assert("┊   ┊   ┻" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : d" in caplog.text)
        assert("┼◇  [Leaf]  : Last" in caplog.text)
        assert("┻" in caplog.text)


    def test_tree_dict(self, caplog):
        data = [
            "First",
            {"Middle" : ["a", {"Nested": ["b", "c"]}, "d"]},
            "Last",
        ]

        obj = FancyReporter()
        obj.tree(data)

        assert("┳" in caplog.text)
        assert("┼◇  [Leaf]  : First" in caplog.text)
        assert("┣─▶─╮" in caplog.text)
        assert("┊   ▼   [Branch] : Middle" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : a" in caplog.text)
        assert("┊   ┣─▶─╮" in caplog.text)
        assert("┊   ┊   ▼   [Branch] : Nested" in caplog.text)
        assert("┊   ┊   ┼◇  [Leaf]  : b" in caplog.text)
        assert("┊   ┊   ┼◇  [Leaf]  : c" in caplog.text)
        assert("┊   ┊   ┻" in caplog.text)
        assert("┊   ┼◇  [Leaf]  : d" in caplog.text)
        assert("┼◇  [Leaf]  : Last" in caplog.text)
        assert("┻" in caplog.text)
