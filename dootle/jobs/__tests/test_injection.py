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

doot._test_setup()
# ##-- 3rd party imports
import doot.errors
from doot.structs import ActionSpec, DKey, TaskName

# ##-- end 3rd party imports

# ##-- 1st party imports
import dootle.jobs.injection as ji

# ##-- end 1st party imports

logging = logmod.root

class TestJobInjection:
    """

    """

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "basic", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_copy(self, spec, state):
        """ the injection copies the value over directly """
        state.update({"a": 2})
        inj       = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(delay=["a"]))
        assert("a" in injection)
        assert(injection['a'] == 2)

    def test_copy_multikey(self, spec, state):
        """ the injection doesn't expand a multikey """
        state.update({"a": "{x} : {y}", "x": 5, "y": 10})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(delay=["a"]))
        assert("a" in injection)
        assert("x" not in injection)
        assert("y" not in injection)
        assert(injection['a'] == "{x} : {y}")

    def test_expand(self, spec, state):
        """ the injection expands the key to its value, adding it under the original key """
        spec.kwargs._table().update({"a_": "b"})
        state.update({"b": 5})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(now=["a"]))
        assert("a" in injection)
        assert(injection['a'] == 5)

    def test_copy_indirect(self, spec, state):
        """ copied indirect key will copy its redirected value
          a_ -> {a:5}
          """
        state.update({"a_": "b", "b": 5})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(delay=["a"]))
        assert("a" in injection)
        assert("a_" not in injection)
        assert(injection['a'] == 5)

    def test_copy_remap(self, spec, state):
        """ copied values can be remapped to new key names """
        state.update({"a": 2})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(delay={"test":"a"}))
        assert("test" in injection)
        assert("a" not in injection)
        assert(injection['test'] == 2)

    def test_expand_remap(self, spec, state):
        """ expanded injections can be remapped to new key names """
        state.update({"a": 2})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(now={"test":"a"}))
        assert("test" in injection)
        assert("a" not in injection)
        assert(injection['test'] == 2)

    def test_replacement(self, spec, state):
        """ keys can be inserted with the defined replacement value """
        state.update({"a": 2})
        inj = ji.JobInjector()
        injection = inj.build_injection(spec, state, dict(insert=["a"]), replacement=10)
        assert("a" in injection)
        assert(injection['a'] == 10)

class TestPathInjection:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "basic", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    @pytest.mark.xfail
    def test_initial(self, spec ,state):
        obj = ji.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

    @pytest.mark.xfail
    def test_inject_shadow(self, spec, state):
        state['shadow_root'] = "blah"
        obj = ji.JobInjectShadowAction()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

class TestNameInjection:

    @pytest.mark.xfail
    def test_initial(self, spec ,state):
        obj = ji.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)

class TestActionInjection:

    @pytest.mark.xfail
    def test_initial(self, spec ,state):
        obj = ji.JobInjectPathParts()
        # build task specs
        # set roots
        # Call:
        result = obj(spec, state)

        # expect these:
        expect = ["lpath", "fstem", "fparent", "fname", "fext", "pstem"]
        assert(False)
