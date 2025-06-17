#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN001, ARG002, C408, PLR2004, ANN201, ANN202, B011
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
from doot.util.dkey import DKey
from doot.workflow import ActionSpec, TaskName, TaskSpec, InjectSpec
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.jobs.expansion import JobExpandAction, MatchExpansionAction

# ##-- end 1st party imports

logging = logmod.root

def static_mapping(_) -> TaskName:
    return TaskName("example::other.task")

##--|

class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "dootle.jobs.expand:JobExpandAction",
                                 "args":[],
                                 "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self, spec, state):
        obj = JobExpandAction()
        assert(isinstance(obj, JobExpandAction))

    def test_empty_expansion(self, spec, state):
        obj     = JobExpandAction()
        result  = obj(spec, state)
        assert(result is None)

    @pytest.mark.parametrize("count", [1,11,2,5,20])
    def test_count_expansion(self, spec, state, count, mocker):
        """ generate a certain number of subtasks """
        mocker.patch("doot.loaded_tasks", {"example::basic": TaskSpec.build({"name":"example::basic"})})
        state['from']      = count
        state['template']  = "example::basic"
        obj                = JobExpandAction()
        result             = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == count)

    def test_list_expansion(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": TaskSpec.build({"name":"example::basic"})})
        args               = ["a", "b", "c"]
        state['inject']    = {"literal": ['target']}
        state['from']      = args
        state['template']  = "example::basic"
        obj                = JobExpandAction()
        result             = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 3)
        for rspec, expect in zip(result['specs'], args, strict=True):
            assert(rspec.target == expect)

    def test_taskname_template(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": TaskSpec.build({"name":"example::basic"})})
        state['template'] = "example::basic"
        state['from']     = [1,2,3]
        obj               = JobExpandAction()
        result            = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))

    def test_basic_expander(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": TaskSpec.build({"name":"example::basic"})})
        state.update(dict(
            _task_name=TaskName("agroup::basic"),
            inject={"literal":["aKey"]},
            template="example::basic"
        ))

        state['from'] = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(len(result['specs']) == 3)

    def test_expander_with_dict_injection(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": TaskSpec.build({"name":"example::basic"})})
        state.update(dict(
            _task_name=TaskName("agroup::basic"),
            inject={"literal": ["aKey"], "from_state":{"other":"{blah}"}},
            template="example::basic"
        ))
        state['from']          = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(all('other' in x.extra for x in result['specs']))
        assert(len(result['specs']) == 3)

class TestMatchExpansionAction:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "dootle.jobs.expansion:MatchExpansionAction"})

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        obj = MatchExpansionAction()
        assert(isinstance(obj, MatchExpansionAction))

    def test_empty_matching(self, spec):
        obj = MatchExpansionAction()
        assert(obj(spec, {"_task_name":TaskName("agroup::basic")}) is None)

    def test_match_call(self, spec, mocker):
        tasks = [TaskSpec.build({"name":x}) for x in ["example::bib.task", "example::txt.task", "example::other.task"]]
        mocker.patch("doot.loaded_tasks", {x.name:x for x in tasks})
        state = {
            "mapping" : {
                ".bib" : "example::bib.task",
                ".txt" : "example::txt.task",
                "_"    : "example::other.task",
            },
            "_task_name": TaskName("agroup::basic"),
            "inject" : {"literal":["val"]},
            "update_" : "specs",
            "from" : [pl.Path(x) for x in ["blah.bib", "blah.txt", "other"]],
        }

        obj     = MatchExpansionAction()
        result  = obj(spec, state)
        assert(result is not None)
        assert('specs' in result)
        for x in result['specs']:
            match x:
                case TaskSpec(name=TaskName() as name, sources=sources) as spec:
                    assert("matched" in name)
                    suff = spec.val.suffix
                    mapped = state['mapping'].get(suff, None) or state['mapping']['_']
                    assert(mapped in sources)
                case x:
                    assert(False), x

    def test_custom_prepfn(self, spec, mocker):
        """
        a custom prepfn that always maps to "example::other.task"
        """
        tasks = [TaskSpec.build({"name":x}) for x in ["example::bib.task", "example::txt.task", "example::other.task"]]
        mocker.patch("doot.loaded_tasks", {x.name:x for x in tasks})
        state = {
            "mapping" : {
                ".bib" : "example::bib.task",
                ".txt" : "example::txt.task",
                "_"    : "example::other.task",
            },
            "_task_name": TaskName("agroup::basic"),
            "inject" : {"literal":["val"]},
            "update_" : "specs",
            "from" : [pl.Path(x) for x in ["blah.bib", "blah.txt", "other"]],
        }

        state['prepfn']  = "fn::dootle.jobs.__tests.test_expansion:static_mapping"
        obj              = MatchExpansionAction()
        result           = obj(spec, state)
        assert(result is not None)
        assert("specs" in result)
        # Now they are all targeted to example::other.task
        for x in result['specs']:
            match x:
                case TaskSpec(sources=xs):
                    assert("example::other.task" in xs)
                case x:
                    assert(False), x
