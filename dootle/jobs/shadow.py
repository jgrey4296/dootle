#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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
import shutil
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
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors
from doot._abstract import Action_p
from doot.mixins.path_manip import PathManip_m
from doot.structs import TaskName, TaskSpec

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.actions.postbox import _DootPostBox

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def _shadow_paths(rpath:pl.Path, shadow_roots:list[pl.Path]) -> list[pl.Path]:
    """ take a relative path, apply it onto a multiple roots to the shadow directories """
    assert(isinstance(rpath, pl.Path))
    assert(not rpath.is_absolute()), rpath
    shadow_dirs = []
    for root in shadow_roots:
        result      = root / rpath
        if result == doot.locs[rpath]:
            raise doot.errors.LocationError("Shadowed Path is same as original", rpath)
        shadow_dirs.append(result.parent)

    return shadow_dirs


##--|
@Proto(Action_p)
@Mixin(PathManip_m, allow_inheritance=True)
class InjectShadowAction:
    """
      Inject a shadow path into each task entry, using the target key which points to the relative path to shadow
      returns the *directory* of the shadow target

    registered as: job.inject.shadow
    """

    @DKeyed.types("onto")
    @DKeyed.paths("shadow_root")
    @DKeyed.redirects("key_")
    def __call__(self, spec, state, _onto, _shadow, _key):
        match _onto:
            case list():
                for x in _onto:
                    rel_path = self._shadow_path(x.extra[_key], _shadow)
                    x.model_extra.update(dict(**x.extra, **{"shadow_path": rel_path}))
            case TaskSpec():
                rel_path = self._shadow_path(_onto.extra[_key], _shadow)
                _onto.model_extra.update(dict(**_onto.extra, **{"shadow_path": rel_path}))

##--|
@Proto(Action_p)
class InjectMultiShadow:
    """
      Inject multiple shadow paths into each task entry, using the target key which
      points to the relative path to shadow
      injects 'shadow_paths', a list of paths

      For use with multibackupaction,
    """
    @DKeyed.types("onto", check=TaskSpec|list)
    @DKeyed.types("shadow_roots", check=list)
    @DKeyed.redirects("key_")
    def __call__(self, spec, state, _onto, _shadow_roots, _key):
        match _onto:
            case list():
                pass
            case TaskSpec() as spec:
                _onto = [spec]

        roots = [DKey(x, mark=DKey.Mark.PATH).expand(spec, state) for x in _shadow_roots]
        for x in _onto:
            updates : list[pl.Path] = _shadow_paths(x.extra[_key], roots)
            x.model_extra.update(dict(**x.extra, **{"shadow_paths": updates}))

##--|
@Proto(Action_p)
class CalculateShadowDirs:
    """
      Take a relative path, and apply it to a list of shadow roots,
      adding 'shadow_paths' to the task state
    """

    @DKeyed.types("shadow_roots")
    @DKeyed.paths("rpath", relative=True)
    def __call__(self, spec, state, _sroots, rpath):
        _sroots = [DKey(x, mark=DKey.Mark.PATH).expand(spec, state) for x in _sroots]
        result : list[pl.Path] = _shadow_paths(rpath,  _sroots)
        return { "shadow_paths" : result}

##--|
@Proto(Action_p)
@Mixin(PathManip_m, allow_inheritance=True)
class MultiBackupAction:
    """
      copy a file somewhere, but only if it doesn't exist at the dest, or is newer than the dest
      The arguments of the action are held in self.spec
      uses 'shadow_paths', a list of directories to backup to,
      using 'pattern', which will be expanded with an implicit variable 'shadow_path'

      will create the destination directory if necessary
    """

    @DKeyed.paths("from")
    @DKeyed.types("pattern")
    @DKeyed.types("shadow_paths", check=list)
    @DKeyed.types("tolerance", check=int, fallback=10_000_000)
    @DKeyed.taskname
    def __call__(self, spec, state, _from, pattern, shadow_paths, tolerance, _name) -> dict|bool|None:
        source_loc = _from
        pattern_key = DKey(pattern, mark=DKey.Mark.PATH)

        doot.report.trace("Backing up : %s", source_loc)
        for shadow_path in shadow_paths:
            match pattern_key.expand({"shadow_path":shadow_path}, spec, state):
                case pl.Path() as x if self._is_write_protected(x):
                    raise doot.errors.LocationError("Tried to write a protected location", x)
                case pl.Path() as x:
                    dest_loc = x
                case x:
                    raise TypeError("Shadow Path Expansion returned bad value", x)

            dest_loc.parent.mkdir(parents=True, exist_ok=True)

            # ExFat FS has lower resolution timestamps
            # So guard by having a tolerance:
            source_ns       = source_loc.stat().st_mtime_ns
            match dest_loc.exists():
                case True:
                    dest_ns = dest_loc.stat().st_mtime_ns
                case False:
                    dest_ns = 1
            source_newer    = source_ns > dest_ns
            difference      = int(max(source_ns, dest_ns) - min(source_ns, dest_ns))
            below_tolerance = difference <= tolerance

            doot.report.detail("Source Newer: %s, below tolerance: %s", source_newer, below_tolerance)
            if (not source_newer) or below_tolerance:
                continue

            doot.report.trace("Destination: %s", dest_loc)
            _DootPostBox.put(_name, dest_loc)
            shutil.copy2(source_loc,dest_loc)
