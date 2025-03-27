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
import re
import time
import types
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.enums import LoopControl_e
from jgdv.structs.strang import CodeReference
import doot
import doot.errors
import sh
from doot.mixins.path_manip import PathManip_m
from doot.structs import TaskName

# ##-- end 3rd party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

git_diff                   = sh.git.bake("--no-pager", "diff", "--name-only")
git_head                   = sh.git.bake("rev-parse", "HEAD")
    
CACHE_PATTERN : Final[str] = "{}.commit_cache"
temp_key                   = DKey("temp!p", implicit=True)

def _build_cache_path(cache:None|pl.Path, taskname:TaskName) -> pl.Path:
    if cache is not None and cache.exists() and cache.is_file():
        return cache

    root_taskname   = taskname.root()
    temp_dir        = temp_key.expand()
    return temp_dir / CACHE_PATTERN.format(root_taskname)

##--|

class GetChangedFilesByCommit:
    """
    Read a cached commit, and the head commit,
    get git log's list of files that have changed

    Like job.walker, will select only files descended from `roots`,
    and with a suffix that matches on in `exts`,
    and passes `fn`, a one arg test function.

    (`recursive` is not used.)

    If cache is not specified, tried to read {temp}/{taskname}.commmit_cache
    If cache does not exist, diffs the past {head_count} commits
    """
    control_e = LoopControl_e

    @DKeyed.types("roots", "exts")
    @DKeyed.references("fn")
    @DKeyed.paths("cache")
    @DKeyed.types("head_count", fallback=1, check=int)
    @DKeyed.taskname
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, roots, exts, fn, cache, head_count, _taskname, _update):
        potentials : list[pl.Path] = []
        match _build_cache_path(cache, _taskname):
            case pl.Path() as x if x.exists() and x.is_file():
                doot.report.trace("Reading Cache: %s", x)
                cached_commit  = x.read_text().strip()
                doot.report.trace("Diffing From %s to HEAD", cached_commit)
                text_result    = git_diff(cached_commit, "HEAD")
                potentials     = [pl.Path(x) for x in text_result.split("\n")]
            case x:
                doot.report.warn("Commit Cache not found for task, expected: %s, Found: %s", cache, x)
                doot.report.warn("Using files from HEAD~%s -> HEAD", head_count)
                text_result    = git_diff(f"HEAD~{head_count}", "HEAD")
                potentials     = [pl.Path(x) for x in text_result.strip().split("\n")]

        result = self._test_files(spec, state, roots, exts, fn, potentials)
        return { _update : result }

    def _test_files(self, spec, state, roots, exts, fn, potentials) -> list[pl.Path]:
        """
          filter found potential files by roots, exts, and a test fn
        """
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        roots   = [DKey(x, mark=DKey.Mark.PATH).expand(spec, state) for x in (roots or [])]
        match fn:
            case CodeReference():
                accept_fn = fn()
            case None:

                def accept_fn(x):
                    return True

        result : list[pl.Path] = []
        for x in potentials:
            if accept_fn(x) in [None, False, self.control_e.no, self.control_e.noBut]:
                continue
            elif (bool(exts) and x.suffix not in exts):
                continue
            elif (bool(roots) and not any(x.resolve().is_relative_to(y) for y in roots)):
                continue
            elif not x.is_file():
                continue

            result.append(x)
        else:
            return result

class CacheGitCommit(PathManip_m):
    """
    Record the head commit hash id in a cache file

    if {cache} is not specified, defaults to {temp}/{taskname}.commit_cache
    """

    @DKeyed.paths("cache", fallback=None)
    @DKeyed.taskname
    def __call__(self, spec, state, cache, _taskname):
        cache = _build_cache_path(cache, _taskname)

        if self._is_write_protected(cache):
            raise doot.errors.LocationError("Tried to cache commit to a write protected location", cache)

        commit = git_head()
        cache.write_text(commit)
