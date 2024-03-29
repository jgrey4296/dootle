#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
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
from doot.control import dir_walker
from doot.control.job import DootJob
from dootle.utils.bookmarks import database_fns as db_fns
from dootle.utils.formats import bookmarks as BC

pl_expand     : Final[Callable] = lambda x: pl.Path(x).expanduser().resolve()
database_name : Final[str]      = doot.config.on_fail("places.sqlite", str).tools.doot.bookmarks.database_name()

class BookmarksUpdate(DootJob):
    """
    ( -> ) copy firefox bookmarks databases, extract, merge with bookmarks file
    """

    def __init__(self, name="bkmk::update", locs=None):
        super().__init__(name, locs)
        self.database                                      = database_name
        self.dbs                                           = []
        self.new_collections : list[BC.BookmarkCollection] = []
        self.total : BC.BookmarkCollection                 = None
        self.temp_dbs                                      = self.locs.temp / "dbs"
        self.locs.ensure("firefox", "temp", "bookmarks_total", task=name)

    def task_detail(self, task):
        bkmks       = self.locs.bookmarks_total
        task.update({
            "actions" : [
                self._get_firefox_dbs,
                (self.mkdirs,  [self.temp_dbs]),
                (self.copy_to, [self.temp_dbs, bkmks], {"fn": "backup"}),
                (self.copy_to, [self.temp_dbs, self.dbs],  {"fn": lambda d,x: d / f"{x.parent.name}_{x.name}" }),
                self._extract,
                self._store_new_extracts,
                (self._merge,  [bkmks]),
                lambda: { "merged": str(self.total)},
                (self.write_to, [bkmks, "merged"]),
            ],
            "file_dep" : [ bkmks ],
        })
        return task

    def _get_firefox_dbs(self):
        self.dbs += self.locs.firefox.rglob(self.database)

    def _extract(self):
        """
        start pony, load db, extract, for each sqlite
        """
        for db_file in self.temp_dbs.glob("*.sqlite"):
            full_path = db_file.resolve()
            self.new_collections.append(db_fns.extract(full_path))

    def _store_new_extracts(self):
        for i, coll in enumerate(self.new_collections):
            (self.temp_dbs / f"extracted_1.bookmarks").write_text(str(coll))

    def _merge(self, fpath, task):
        """
        load total.bookmarks, merge extracted
        """
        self.total = BC.BookmarkCollection.read(fpath)
        original_amnt = len(self.total)
        for extracted in self.new_collections:
            self.total += extracted
            self.total.merge_duplicates()
        logging.info(f"Bookmark Count: {original_amnt} -> {len(self.total)}")

class BookmarksCleaner(DootJob):
    """
    clean bookmarks file, removing duplicates, stripping urls
    """

    def __init__(self, name="bkmk::clean", locs=None):
        super().__init__(name, locs)
        self.total = None
        self.locs.ensure("temp", "bookmarks", task=name)

    def task_detail(self, task):
        fpath =  self.locs.bookmarks/ "total.bookmarks"
        task.update({
            "actions"  : [
                (self.copy_to, [self.locs.temp, fpath], {"fn": "backup"}),
                (self._merge, [fpath]),
                lambda: {"merged": str(self.total)},
                (self.write_to, [fpath, "merged"]),
            ],
            "file_dep" : [ fpath ],
        })
        return task

    def _merge(self, fpath):
        self.total = BC.BookmarkCollection.read(fpath)
        self.total.merge_duplicate()

class TODOBookmarksSplit(DootJob):
    """
    TODO Create several bookmarks files of selections
    """
    pass
