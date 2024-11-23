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
import sh
from doot.enums import LoopControl_e
from doot.mixins.path_manip import PathManip_m
from doot.structs import DKey, DKeyed, TaskName
from jgdv.structs.code_ref import CodeReference

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

# or use --no-pager for git
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
                printer.info("Reading Cache: %s", x)
                cached_commit  = x.read_text().strip()
                printer.info("Diffing From %s to HEAD", cached_commit)
                text_result    = git_diff(cached_commit, "HEAD")
                potentials     = [pl.Path(x) for x in text_result.split("\n")]
            case x:
                printer.warning("Commit Cache not found for task, expected: %s, Found: %s", cache, x)
                printer.warning("Using files from HEAD~%s -> HEAD", head_count)
                text_result    = git_diff(f"HEAD~{head_count}", "HEAD")
                potentials     = [pl.Path(x) for x in text_result.strip().split("\n")]

        result = self._test_files(spec, state, roots, exts, fn, potentials)
        return { _update : result }

    def _test_files(self, spec, state, roots, exts, fn, potentials) -> list[pl.Path]:
        """
          filter found potential files by roots, exts, and a test fn
        """
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        roots   = [DKey(x, mark=DKey.mark.PATH).expand(spec, state) for x in (roots or [])]
        match fn:
            case CodeReference():
                accept_fn = fn.try_import()
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
            raise doot.errors.DootLocationError("Tried to cache commit to a write protected location", cache)

        commit = git_head()
        cache.write_text(commit)
