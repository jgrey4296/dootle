#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
import itertools
import functools
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import doot
from doot import globber, tasker

from hashlib import sha256
from doit.exceptions import TaskFailed
from collections import defaultdict
import fileinput
import re

from doot.mixins.commander import CommanderMixin
from doot.mixins.batch import BatchMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.filer import FilerMixin

batch_size   : Final[int]= doot.config.on_fail(10, int).batch.size()

hash_record  : Final[str] = doot.config.on_fail(".hashes", str).files.hash.record()
hash_concat  : Final[str] = doot.config.on_fail(".all_hashes", str).files.hash.grouped()
hash_dups    : Final[str] = doot.config.on_fail(".dup_hashes", str).files.hash.duplicates()

class HashAllFiles(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, BatchMixin):
    """
    ([data] -> data) For each subdir, hash all the files in it to .hashes

    """

    def __init__(self, name="hash::files", locs:DootLocData=None, roots=None, exts=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=exts, rec=rec)
        self.current_hashed = {}
        self.hash_record    = hash_record
        self.check_fn       = lambda x: x.is_file() and x.name[0] != "."

    def set_params(self):
        return self.target_params()

    def clean(self, task):
        for root in self.roots:
            for fpath in root.rglob(self.hash_record):
                logging.info("Would Delete: %s", fpath)

    def filter(self, fpath):
        if fpath.is_file():
            return self.control.discard

        for x in fpath.iterdir():
            if self.check_fn(x):
                return self.control.accept

        return self.control.discard

    def subtask_detail(self, task, fpath):
        hash_file = fpath / self.hash_record

        task.update({
            "actions" : [
                (self.load_hashed, hash_file),
                (self.hash_dir, fpath, hash_file)
            ],
            "targets" : [ hash_file ],
        })
        return task

    def load_hashed(self, fpath):
        self.current_hashed.clear()
        if not fpath.exists():
            return

        hashes              = [x.split(" ") for x in fpath.read_text().split("\n") if bool(x)]
        self.current_hashed = {" ".join(xs[1:]).strip():xs[0] for xs in hashes}

    def sub_filter(self, fpath):
        if fpath.is_file() and fpath.name != self.hash_record and str(fpath) not in self.current_hashed:
            return self.globc.keep
        return self.globc.discard

    def hash_dir(self, fpath, hash_file):
        """
        Glob for applicable directories
        """
        chunks = self.chunk(self.glob_target(fpath, rec=False, fn=self.sub_filter))
        self.run_batches(*chunks, hash_file=hash_file)

    def batch(self, data, hash_file=None):
        """
        For each applicable directory, hash files as necessary
        """
        if not bool(data):
            return
        try:
            logging.info("Batch Count: %s (size: %s)", self.batch_count, len(data))
            # -r puts the hash first, making it easier to run `uniq` later
            act = self.make_cmd("md5", "-r", *data)
            act.execute()
            with open(hash_file, 'a') as f:
                print(act.out, file=f)

        except TypeError as err:
            print(err, file=sys.stderr)
            raise err

class GroupHashes(tasker.DootTasker, CommanderMixin, FilerMixin):
    """
    Concat all .hashes files together, to prep for duplicate detection
    """

    def __init__(self, name="hash::concat", locs=None):
        super().__init__(name, locs)
        self.hash_record    = hash_record
        self.hash_concat    = hash_concat
        self.output         = locs.temp / self.hash_concat
        self.locs.ensure("data", task=name)

    def setup_detail(self, task):
        task.update({
            "actions" : [
                (self.rmfiles, [self.output]),
                self.make_cmd("touch", self.output),
            ],
        })
        return task

    def task_detail(self, task):
        task.update({
            "targets" : [ self.output ],
            "actions" : [ self.concat_hash_files ],
            "clean"   : True,
        })
        return task

    def concat_hash_files(self):
        globbed = list(self.locs.data.rglob(self.hash_record))
        if not bool(globbed):
            return

        with open(self.output, "w") as allHashes:
            for line in fileinput.input(files=globbed):
                print(line, end="", file=allHashes)

class DetectDuplicateHashes(tasker.DootTasker, CommanderMixin, FilerMixin):
    """
    sort all_hashes, and run uniq of the first n chars
    """

    def __init__(self, name="hash::dups", locs=None):
        super().__init__(name, locs)
        self.hash_collection = defaultdict(lambda: set())
        self.hash_concat     = self.locs.temp / hash_concat
        self.output          = self.locs.build / hash_dups
        self.locs.ensure("temp", task=name)

    def task_detail(self, task):
        task.update({
            "actions"  : [
                self.read_hashes,
                self.identify_duplicates, #-> duplicates
                (self.write_to, [self.output, "duplicates"]),
            ],
            "file_dep" : [ self.hash_concat ],
            "targets"  : [ self.output ],
        })
        return task

    def read_hashes(self):
        for line in self.hash_concat.read_text().split("\n"):
            if not bool(line):
                continue
            # split into (`hash` `filepath`)
            parts = line.strip().split(" ")
            fpath = pl.Path(" ".join(parts[1:]).strip())
            if fpath.exists():
                self.hash_collection[parts[0]].add(fpath)

    def identify_duplicates(self):
        duplicates = []
        for hash_key, fpaths in self.hash_collection.items():
            match len(fpaths):
                case 0:
                    raise ValueError("Hash Collecion shouldn't be able to have a hash key without associated file")
                case 1:
                    # has no duplicates
                    continue
                case _:
                    # more than one file with the hash
                    fnames_joined = " : ".join(sorted(map(str, fpaths)))
                    dup_line      = f"{hash_key} : {fnames_joined}"
                    duplicates.append(dup_line)

        dup_str = "\n".join(duplicates)
        return {'duplicates': dup_str}

    def clean(self, task):
        globbed = list(self.locs.data.rglob(self.hash_record))
        if not bool(globbed):
            return

        current_file = None
        current_set  = set()
        for line in fileinput.input(files=globbed, inplace=True):
            if fileinput.isfirstline():
                current_file = fileinput.filename()
                current_set.clear()

            if not bool(line.strip()):
                continue

            parts    = line.strip().split(" ")
            hash_val = parts[0]
            fpath    = pl.Path(" ".join(parts[1:]).strip())
            if hash_val in current_set:
                continue
            if not fpath.exists():
                continue
            if fpath.name[0] == ".":
                continue

            current_set.add(hash_val)
            print(line.strip())

class MarkDuplicates(tasker.DootTasker, FilerMixin):
    """
    Delete duplicates, using a set heuristic

    heuristics:
    delete  oldest/newest
    prefer  locations [xs]
    protect locations [ys]
    """

    def __init__(self, name="hash::dups.mark", locs=None, output=None):
        super().__init__(name, locs)
        self.target         = self.locs.build / hash_dups
        self.num_re         = re.compile(r"\(\d+\)$")
        self.output         = output or self.locs.build / "to_delete"
        self.delete_queue   = []
        self.chosen_process = None

    def set_params(self):
        return [
            {"name": "samedir", "short": "s", "type": bool, "default": False},
            {"name": "root", "long": "root", "type": pl.Path, "default": self.locs.data },

            {"name": "prefer", "long": "pref", "type": str, "default": None},
            {"name": "preferenceFocus", "long": "pref-focus", "type": str, "default": "parent", "choices": [("parent", "Filter by the parent name"),
                                                                                                            ("root", "Filter by the root name")]},
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.choose_selection_process,
                self.select_duplicates,
                self.write_deletion_queue,
            ],
        })
        return task

    def choose_selection_process(self):
        """
        select and prepare the filter process
        """
        process = lambda xs: ([], None)
        match self.args:
            case { "samedir": True}:
                process = self._select_in_same_dir
            case { "prefer" : pair} if pair is not None:
                prefs = pair.split("<")
                process = functools.partial(self._select_preferring, prefs)

            case _:
                logging.info("No Applicable heuristic selected")

        self.chosen_process = process

    def select_duplicates(self):
        """
        run through all duplicates, and delete ones that the process says to
        """
        for line in self.target.read_text().split("\n"):
            if not bool(line.strip()):
                continue

            parts = line.split(" : ")
            if len(parts) < 3:
                logging.warning("Bad hash line: ", line)

            fpaths   = [pl.Path(x.strip()) for x in parts[1:]]
            suitable = [x for x in fpaths if x.is_relative_to(self.args['root']) and x.exists()]
            if not bool(suitable) or len(suitable) < 2:
                continue

            to_delete, keeper = self.chosen_process(suitable)
            self.queue_deletions(to_delete, keeper)

    def _select_in_same_dir(self, dups):
        """
        delete duplicates in the same directory if they end with (\d+) before .ext
        """
        parent_dirs = defaultdict(lambda: set())
        for fpath in dups:
            parent_dirs[str(fpath.parent)].add(fpath)

        results = []
        for group in parent_dirs.values():
            if len(group) < 2:
                continue

            available = [x for x in group if self.num_re.search(x.stem)]
            if len(available) >= len(group):
                continue

            results += available

        return results, None

    def _select_preferring(self, prefs, dups):
        """
        select by preferring according to a specified root, ignore everything else
        """
        sel_fn = lambda x: x.parent.name
        if self.args['preferenceFocus'] == "root":
            sel_fn = lambda x: x.parts[0]
        pref_dict            = {y:x for x,y in enumerate(prefs, 1)}
        matching             = [(x,pref_dict.get(sel_fn(x), -10)) for x in dups]
        only_preferences     = [x for x in matching if x[1] > 0]
        sorted_by_preference = sorted(only_preferences, key=lambda x: x[1])
        to_delete            = sorted_by_preference[:-1]

        if not bool(to_delete):
            return [], None

        keeper               = sorted_by_preference[-1][0]
        return [x[0] for x in to_delete], keeper

    def queue_deletions(self, delete_list, keeper):
        if not bool(delete_list):
            return

        resolved_keeper = keeper.resolve()
        self.delete_queue += [x for x in delete_list if not x.resolve().samefile(resolved_keeper)]
        for fpath in delete_list:
            # Ignore files that are the same as the keeper
            if not fpath.resolve().samefile(keeper.resolve()):
                self.delete_queue.append((delete_list, keeper))

    def write_deletion_queue(self):
        self.output.write_text("\n".join(map(str, self.delete_queue)))
