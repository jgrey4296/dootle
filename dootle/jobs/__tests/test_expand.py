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
from doot.workflow.factory import TaskFactory, DelayedSpec
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

from dootle.jobs.expand import JobExpandAction, MatchExpansionAction, JobQueueAction
from doot.workflow._interface import TaskName_p

logging = logmod.root
logmod.getLogger("jgdv").propagate = False
factory = TaskFactory()

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
        return {"_task_name": TaskName("agroup::basic").to_uniq()}

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
        mocker.patch("doot.loaded_tasks", {"example::basic": factory.build({"name":"example::basic"})})
        state['from']      = count
        state['template']  = "example::basic"
        obj                = JobExpandAction()
        result             = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == count)

    def test_list_expansion(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": factory.build({"name":"example::basic"})})
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
            assert(rspec.base == "example::basic")
            assert(rspec.applied['target'] == expect)

    def test_taskname_template(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": factory.build({"name":"example::basic"})})
        state['template'] = "example::basic"
        state['from']     = [1,2,3]
        obj               = JobExpandAction()
        result            = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))

    def test_basic_expander(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": factory.build({"name":"example::basic"})})
        state.update(dict(
            _task_name=TaskName("agroup::basic").to_uniq(),
            inject={"literal":["aKey"]},
            template="example::basic"
        ))

        state['from'] = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(len(result['specs']) == 3)
        for x in result['specs']:
            assert(isinstance(x, DelayedSpec))
            assert(x.applied['aKey'] in ["first", "second", "third"])

    def test_expander_with_dict_injection(self, spec, state, mocker):
        mocker.patch("doot.loaded_tasks", {"example::basic": factory.build({"name":"example::basic"})})
        state.update(dict(
            _task_name=TaskName("agroup::basic").to_uniq(),
            inject={"literal": ["aKey"], "from_state":{"other":"{blah}"}},
            template="example::basic"
        ))
        state['from']          = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(len(result['specs']) == 3)
        for x in result['specs']:
            assert(isinstance(x, DelayedSpec))
            assert(x.applied['aKey'] in ["first", "second", "third"])
            assert('other' in x.applied)

class TestMatchExpansionAction:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "dootle.jobs.expand:MatchExpansionAction"})

    @pytest.fixture(scope="function")
    def task_map(self):
        return {
            ".bib" : "example::bib.task",
            ".txt" : "example::txt.task",
            "_"    : "example::other.task",
        }

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_ctor(self):
        obj = MatchExpansionAction()
        assert(isinstance(obj, MatchExpansionAction))

    def test_empty_matching(self, spec):
        obj = MatchExpansionAction()
        assert(obj(spec, {"_task_name":TaskName("agroup::basic").to_uniq()}) is None)

    def test_match_call(self, spec, mocker, task_map):
        tasks = [factory.build({"name":x}) for x in ["example::bib.task", "example::txt.task", "example::other.task"]]
        mocker.patch("doot.loaded_tasks", {x.name:x for x in tasks})
        state = {
            "_task_name"  : TaskName("agroup::basic").to_uniq(),
            "mapping"     : task_map,
            "inject"      : {"literal":["val"]},
            "from"        : [pl.Path(x) for x in ["blah.bib", "blah.txt", "other"]],
            "update_"     : "specs",
        }

        obj     = MatchExpansionAction()
        result  = obj(spec, state)
        assert(result is not None)
        assert('specs' in result)
        for x in result['specs']:
            match x:
                case DelayedSpec() as spec:
                    assert("matched" in spec.target)
                    suff = spec.applied['val'].suffix
                    mapped = task_map.get(suff, None) or task_map['_']
                    assert(mapped == spec.base)
                case x:
                    assert(False), x

    def test_custom_prepfn(self, spec, mocker, task_map):
        """
        a custom prepfn that always maps to "example::other.task"
        """
        expectation  = static_mapping("")
        tasks        = [factory.build({"name":x}) for x in ["example::bib.task", "example::txt.task", "example::other.task"]]
        mocker.patch("doot.loaded_tasks", {x.name:x for x in tasks})
        state = {
            "mapping"     : task_map,
            "_task_name"  : TaskName("agroup::basic").to_uniq(),
            "inject"      : {"literal":["val"]},
            "update_"     : "specs",
            "from"        : [pl.Path(x) for x in ["blah.bib", "blah.txt", "other"]],
        }

        state['prepfn']  = static_mapping
        obj              = MatchExpansionAction()
        result           = obj(spec, state)
        assert(result is not None)
        assert("specs" in result)
        # Now they are all targeted to example::other.task
        for x in result['specs']:
            match x:
                case DelayedSpec() as spec:
                    assert(spec.base == expectation)
                case x:
                    assert(False), x


    def test_custom_prepfn_coderef(self, spec, mocker, task_map):
        """
        a custom prepfn that always maps to "example::other.task"
        """
        expectation  = static_mapping("")
        tasks        = [factory.build({"name":x}) for x in ["example::bib.task", "example::txt.task", "example::other.task"]]
        mocker.patch("doot.loaded_tasks", {x.name:x for x in tasks})
        state = {
            "mapping"     : task_map,
            "_task_name"  : TaskName("agroup::basic").to_uniq(),
            "inject"      : {"literal":["val"]},
            "update_"     : "specs",
            "from"        : [pl.Path(x) for x in ["blah.bib", "blah.txt", "other"]],
        }

        state['prepfn']  = "fn::dootle.jobs.__tests.test_expand:static_mapping"
        obj              = MatchExpansionAction()
        result           = obj(spec, state)
        assert(result is not None)
        assert("specs" in result)
        # Now they are all targeted to example::other.task
        for x in result['specs']:
            match x:
                case DelayedSpec() as spec:
                    assert(spec.base == expectation)
                case x:
                    assert(False), x

class TestJobQueue:

    @pytest.fixture(scope="function")
    def act(self, mocker):
        return JobQueueAction()

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "dootle.jobs.expand:JobQueueAction",
                                 "args":[],
                                 })

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        obj = JobQueueAction()
        assert(isinstance(obj, JobQueueAction))

    def test_empty_queue(self, act, spec):
        match act(spec, {}):
            case None | []:
                assert(True)
            case x:
                assert(False), x

    def test_simple_args(self, act, spec):
        spec.args = ["simple::a.b.c", "simple::d.e.f"]
        match act(spec, {}):
            case [*xs]:
                assert(len(xs) == 2)
                assert(all(isinstance(x, TaskName_p) for x in xs))
            case x:
                assert(False), x

    def test_with_specs(self, act):
        spec = ActionSpec.build({
            "do": "dootle.jobs.expand:JobQueueAction",
            "from_" : "specs",
        })
        state = {
            "specs" : [
                DelayedSpec(base="simple::base",
                            target="actual::task..1",
                            overrides={}),
                DelayedSpec(base="simple::base",
                            target="actual::task..2",
                            overrides={}),
            ]
        }

        match act(spec, state):
            case [*xs]:
                assert(len(xs) == 2)
                assert(all(isinstance(x, DelayedSpec) for x in xs))
            case x:
                assert(False), x


    def test_with_args_and_specs(self, act):
        spec = ActionSpec.build({
            "do"     : "dootle.jobs.expand:JobQueueAction",
            "args"   : ["blah::a", "bloo::b", "aweg::c"],
            "from_"  : "specs",
        })
        state = {
            "specs" : [
                DelayedSpec(base="simple::base",
                            target="actual::task..1",
                            overrides={}),
                DelayedSpec(base="simple::base",
                            target="actual::task..2",
                            overrides={}),
            ]
        }

        match act(spec, state):
            case [*xs]:
                assert(len(xs) == 5)
                assert(all(isinstance(x, TaskName_p|DelayedSpec) for x in xs))
            case x:
                assert(False), x
