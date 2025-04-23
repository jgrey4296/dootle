#!/usr/bin/env python3
"""
  Injection adds to a task spec.
  allowing initial state, extra actions, etc.

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
import random
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
import doot
import doot.errors
from doot._abstract import Action_p
from doot.mixins.path_manip import PathManip_m
from doot.structs import TaskName, TaskSpec, ActionSpec, InjectSpec

# ##-- end 3rd party imports

# ##-- types
# isort: off
if TYPE_CHECKING:
   from jgdv import Maybe

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Action_p)
class JobInjector:
    """ Inject data into task specs. ::

        inject={copy=[Xs], expand={Yks : Yvs}, replace=[Zs]}

    ::

        'copy'    : redirects, and copies without further expansion : [a_,x] -> {a:2, x:{q}}
        'expand'  : redirects, expands, then copies                 : [a_,x] -> {a:2, x:5}
        'replace' : sets keys to whatever replace value is passed in (for job.expand)

    X,Y can be lists or dicts, for simple setting, or remapping
    Z is just a straight list

    registered as: job.injector
    """

    @DKeyed.types("onto", "inject")
    def __call__(self, spec, state, onto, inject):
        match InjectSpec.build(inject, sources=[spec, state]):
            case None:
                injection = {}
            case x:
                injection = x.as_dict(constraint=spec)

        match onto:
            case list():
                for x in onto:
                    x.model_extra.update(dict(**x.extra, **injection))
            case TaskSpec():
                onto.model_extra.update(dict(**x.extra, **injection))

@Proto(Action_p)
class JobPrependActions:
    """

    registered as: job.actions.prepend
    """

    @DKeyed.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        action_specs = [ActionSpec.build(x) for x in _actions]
        for x in _onto:
            actions = action_specs + x.actions
            x.actions = actions

@Proto(Action_p)
class JobAppendActions:
    """

    registered as: job.actions.append
    """

    @DKeyed.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        action_specs = [ActionSpec.build(x) for x in _actions]
        for x in _onto:
            x.actions += action_specs

@Proto(Action_p)
@Mixin(PathManip_m, allow_inheritance=True)
class JobInjectPathParts:
    """
      Map lpath, fstem, fparent, fname, fext onto each
      taskspec in the `onto` list, using each spec's `key`

    registered as: job.inject.path.elements
    """

    @DKeyed.types("onto", "roots")
    @DKeyed.redirects("key_")
    def __call__(self, spec, state, _onto, roots, _key):
        root_paths = self._build_roots(spec, state, roots)
        match _onto:
            case list():
                for x in _onto:
                    data = x.params
                    data.update(self._calc_path_parts(x.extra[_key], root_paths))
                    x.model_extra.update(data)
            case TaskSpec():
                data = dict(x.extra)
                data.update(self._calc_path_parts(_onto.extra[_key], root_paths))
                _onto.model_extra.update(data)

@Proto(Action_p)
class JobSubNamer:
    """
      Apply the name {basename}.{i}.{key} to each taskspec in {onto}

    registered as: job.sub.name
    """

    @DKeyed.taskname
    @DKeyed.expands("keylit")
    @DKeyed.types("onto")
    def __call__(self, spec, state, _basename, _key, _onto):
        match _onto:
            case list():
                for i,x in enumerate(_onto):
                    val = x.extra[_key]
                    x.name = _basename.push(i, self._gen_subname(val))
            case TaskSpec():
                _onto.name = _basename.push(self._gen_subname(val))

    def _gen_subname(self, val) -> str:
        match val:
            case pl.Path():
                return val.stem
            case str():
                return val
