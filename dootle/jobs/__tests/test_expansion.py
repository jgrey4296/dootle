#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN001, ARG002, C408, PLR2004, ANN201
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
import doot.errors
import pytest

# ##-- end 3rd party imports

doot._test_setup()
# ##-- 3rd party imports
from doot.structs import ActionSpec, DKey, TaskName, TaskSpec

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.jobs.expansion import JobExpandAction, JobMatchAction

# ##-- end 1st party imports

logging = logmod.root

class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "dootle.jobs.expand:JobExpandAction", "args":[], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self, spec, state):
        obj = JobExpandAction()
        assert(isinstance(obj, JobExpandAction))

    def test_empty_expansion(self, spec, state):
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 0)

    @pytest.mark.parametrize("count", [1,11,2,5,20])
    def test_count_expansion(self, spec, state, count):
        """ generate a certain number of subtasks """
        spec.kwargs._table()['from'] = count
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == count)

    def test_list_expansion(self, spec, state):
        args = ["a", "b", "c"]
        spec.kwargs._table()['from'] = args
        state['inject'] = {"insert": ['target']}
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 3)
        for rspec, expect in zip(result['specs'], args, strict=True):
            assert(rspec.target == expect)

    def test_action_template(self, spec, state):
        state['template'] = "test::task"
        state['from']     = [1]
        obj               = JobExpandAction()
        result            = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(result['specs'][0].sources == ["test::task"])
        assert(len(result['specs'][0].actions) == 0)

    def test_taskname_template(self, spec, state):
        state['template'] = [{"do":"basic"}, {"do":"basic"}, {"do":"basic"}]
        state['from']     = [1]
        obj               = JobExpandAction()
        result            = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs'][0].actions) == 3)

    def test_basic_expander(self, spec, state):
        state.update(dict(_task_name=TaskName("agroup::basic"),
                          inject={"insert":["aKey"]},
                          base="base::task"))

        state['from'] = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(len(result['specs']) == 3)

    def test_expander_with_dict_injection(self, spec, state):
        state.update(dict(_task_name=TaskName("agroup::basic"),
                          inject={"insert": ["aKey"], "delay":{"other":"blah"}},
                          base="base::task"))

        state['from']          = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(all('other' in x.extra for x in result['specs']))
        assert(len(result['specs']) == 3)

class TestJobMatcher:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        pass
