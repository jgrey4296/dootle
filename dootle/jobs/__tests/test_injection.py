#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, B011, ANN001
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

import doot.errors
from doot.workflow import ActionSpec, TaskName
from doot.util import DelayedSpec
import dootle.jobs.injection as JI  # noqa: N812

logging = logmod.root
logmod.getLogger("jgdv").propagate = False

class TestJobInjector:


    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        obj = JI.JobInjector()
        assert(isinstance(obj, JI.JobInjector))

    def test_no_op(self):
        obj = JI.JobInjector()
        spec = ActionSpec.build({"do":"job.injector", "onto_":"specs",
                                 "inject": {"from_state":[]},
                                 })
        state = {"specs":[]}
        match obj(spec, state):
            case None:
                assert(True)
            case x:
                assert(False), x


    def test_simple_inject(self):
        obj = JI.JobInjector()
        inject = {"from_state" : ["val"]}
        spec = ActionSpec.build({"do":"job.injector", "onto_":"specs",
                                 "inject": inject,
                                 })
        delayed = [DelayedSpec(base="some::task",
                               target="some::target",
                               overrides={}),
                   DelayedSpec(base="some::other",
                               target="another::target",
                               overrides={}),
                   ]
        state = {"specs":delayed,
                 "val" : "blah",
                 }
        for x in delayed:
            assert("val" not in x.applied)
        obj(spec, state)
        for x in delayed:
            assert("val" in x.applied)





@pytest.mark.skip
class TestPathInjection:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "basic",
                                 "args":["test::simple", "test::other"],
                                 "update_":"specs"})

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
