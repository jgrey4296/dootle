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

from doot.reporters import _interface as API

##--|
from .. import LineReporter
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

# Body:

class TestLineReporter:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        match LineReporter():
            case API.WorkflowReporter_p():
                assert(True)
            case x:
                 assert(False), x

    def test_basic_trace(self, caplog):
        obj = LineReporter()
        obj.root()
        obj.act("test", "blah")
        obj.finished()
        assert("┳" in caplog.text)
        assert("┼◇  [test]  : blah" in caplog.text)
        assert("┻" in caplog.text)

    def test_ctx_manager(self):
        obj = LineReporter()
        assert(obj.level == 0)
        with obj:
            assert(obj.level == 1)

        assert(obj.level == 0)

    def test_branch(self, caplog):
        obj = LineReporter()
        with obj.branch("Test"):
            assert(obj.level == 1)
            obj.act("Log", "blah")
            obj.result("blah")

        assert("┣─▶╮" in caplog.text)
        assert("┊  ▼   [Test]  : " in caplog.text)
        assert("┊  ┼◇  [Log]   : blah" in caplog.text)
        assert("┢◀─╯   []      : blah" in caplog.text)


    def test_double_branch(self, caplog):
        obj = LineReporter()
        with obj.branch("first"):
            assert(obj.level == 1)
            obj.act("Log", "act1")

            with obj.branch("second"):
                obj.act("Log", "act2")
                obj.act("Log", "act3")
                obj.result("second")

            obj.act("Log", "act4")
            obj.result("first")

        assert("┣─▶╮" in caplog.text)
        assert("┊  ▼   [first] : " in caplog.text)
        assert("┊  ┼◇  [Log]   : act1" in caplog.text)
        assert("┊  ┣─▶╮" in caplog.text)
        assert("┊  ┊  ▼   [second] : " in caplog.text)
        assert("┊  ┊  ┼◇  [Log]   : act2" in caplog.text)
        assert("┊  ┊  ┼◇  [Log]   : act3" in caplog.text)
        assert("┊  ┢◀─╯   []      : second" in caplog.text)
        assert("┊  ┼◇  [Log]   : act4" in caplog.text)
        assert("┢◀─╯   []      : first" in caplog.text)

    ##--|

    @pytest.mark.skip
    def test_todo(self):
        pass
