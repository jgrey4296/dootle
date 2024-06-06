#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

from __future__ import annotations

import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
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

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import random
import shutil
from tomlguard import TomlGuard
import doot
import doot.errors
from doot._abstract import Action_p
from doot.structs import DootKey, TaskSpec, TaskName, CodeReference
from doot.mixins.path_manip import PathManip_m
from doot.actions.postbox import _DootPostBox

class InjectMultiShadow:
    """
      Inject multiple shadow paths into each task entry, using the target key which
      points to the relative path to shadow
      injects 'shadow_paths', a list of paths

      For use with multibackupaction,
    """

    @DootKey.dec.types("onto", hint={"type_": TaskSpec|list})
    @DootKey.dec.types("shadow_roots")
    @DootKey.dec.redirects("key_")
    def __call__(self, spec, state, _onto, _shadow_roots, _key):
        match _onto:
            case list():
                pass
            case TaskSpec() as spec:
                _onto = [spec]

        roots = [DootKey.build(x).to_path(spec, state) for x in _shadow_roots]
        for x in _onto:
            updates : list[pl.Path] = self._shadow_paths(x.extra[_key], roots)
            x.model_extra.update(dict(**x.extra, **{"shadow_paths": updates}))


    def _shadow_paths(self, rpath:pl.Path, shadow_roots:list[pl.Path]) -> list[pl.Path]:
        """ take a relative path, apply it onto a multiple roots to the shadow directories """
        assert(isinstance(rpath, pl.Path))
        assert(not rpath.is_absolute())
        shadow_dirs = []
        for root in shadow_roots:
            result      = root / rpath
            if result == doot.locs[rpath]:
                raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)
            shadow_dirs.append(result.parent)

        return shadow_dirs


class MultiBackupAction(PathManip_m):
    """
      copy a file somewhere, but only if it doesn't exist at the dest, or is newer than the dest
      The arguments of the action are held in self.spec
      uses 'shadow_paths', a list of directories to backup to,
      using 'pattern', which will be expanded with an implicit variable 'shadow_path'

      will create the destination directory if necessary
    """

    @DootKey.dec.paths("from")
    @DootKey.dec.types("pattern")
    @DootKey.dec.types("shadow_paths")
    @DootKey.dec.taskname
    def __call__(self, spec, state, _from, pattern, shadow_paths, _name) -> dict|bool|None:
        source_loc = _from
        pattern_key = DootKey.build(pattern)
        for shadow_path in shadow_paths:
            state['shadow_path'] = shadow_path
            dest_loc             = pattern_key.to_path(spec, state)

            if self._is_write_protected(dest_loc):
                raise doot.errors.DootLocationError("Tried to write a protected location", dest_loc)


            dest_loc.parent.mkdir(parents=True, exist_ok=True)

            if dest_loc.exists() and source_loc.stat().st_mtime_ns <= dest_loc.stat().st_mtime_ns:
                continue

            printer.warning("Backing up : %s", source_loc)
            printer.warning("Destination: %s", dest_loc)
            _DootPostBox.put(_name, dest_loc)
            shutil.copy2(source_loc,dest_loc)
        else:
            del state['shadow_path']
