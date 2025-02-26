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
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import pytest

# ##-- end 3rd party imports

# ##-- 3rd party imports
import doot.errors
from doot.structs import ActionSpec, DKey, TaskName

# ##-- end 3rd party imports

# ##-- 1st party imports
import dootle.jobs.injection as JI

# ##-- end 1st party imports

logging = logmod.root

@pytest.mark.skip
class TestPathInjection:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "basic", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, spec ,state):
        obj = JI.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

    def test_inject_shadow(self, spec, state):
        state['shadow_root'] = "blah"
        obj = JI.JobInjectShadowAction()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

@pytest.mark.skip
class TestNameInjection:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, spec ,state):
        obj = JI.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

@pytest.mark.skip
class TestActionInjection:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, spec ,state):
        obj = JI.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)
