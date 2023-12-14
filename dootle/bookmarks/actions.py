#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
import doot.errors
from doot._abstract import Action_p
import doot.utils.expansion as exp

from dootle.bookmarks.db_fns import extract
from dootle.bookmarks import structs as BC

printer = logmod.getLogger("doot._printer")

##-- expansion keys
FROM_KEY = exp.DootKey("from")
UPDATE   = exp.DootKEy("update_")

##-- end expansion keys

class BookmarksPonyExtraction(Action_p):
    """
      extract bookmarks from a sqlite firefox db using pony
    """
    _toml_kwargs = ["from", "update_", "debug"]

    def __call__(self, spec, task_state):
        db_loc         = FROM_KEY.to_path(spec, task_state)
        update_key     = UPDATE.redirect(spec)
        debug          = spec.kwargs.on_fail(False).debug()
        try:
            printer.info("Starting Extraction")
            result       = extract(db_loc, debug=debug)
            printer.info("Extraction Complete: %s results", len(result))
            return { update_key : result }
        except Exception as err:
            raise doot.errors.DootActionError("Pony Errored: %s", str(err)) from err


class BookmarksLoad(Action_p):

    _toml_kwargs = ["from", "update_"]

    def __call__(self, spec, task_state):
        load_path = FROM_KEY.to_path(spec, task_state)
        data_key  = UPDATE.redirect(spec)
        printer.info("Loading Bookmarks from: %s", load_path)
        result    = BC.BookmarkCollection.read(load_path)
        printer.info("Loaded %s Bookmarks", len(result))
        return { data_key : result }

class BookmarksMerge(Action_p):

    _toml_kwargs = ["from", "update_"]

    def __call__(self, spec, task_state):
        data_key                                 = UPDATE.redirect(spec)
        source_data : set[BC.BookmarkCollection] = FROM_KEY.to_any(spec, task_state, type_=set)

        merged = BC.BookmarkCollection()
        for x in source_data:
            match x:
                case BC.BookmarkCollection():
                    pre_count = len(merged)
                    merged += x
                    growth = len(merged) - pre_count
                    printer.info("Added %s bookmarks, Total Growth: %s", len(x), growth)
                case _:
                    raise doot.errors.DootActionError("Unknown type tried to merge into bookmarks", x)

        return { data_key : merged }

class BookmarksToStr(Action_p):
    _toml_kwargs = ["update_", "from"]

    def __call__(self, spec, task_state):
        data_key                                      = UPDATE.redirect(spec)
        source_data : BC.BookmarkCollection           = FROM_KEY.to_any(spec, task_state, type_=BC.BookmarkCollection)

        printer.info("Writing Bookmark Collection of size: %s", len(source_data))
        return { data_key : str(source_data) }


class BookmarksRemoveDuplicates(Action_p):
    _toml_kwargs = ["from"]

    def __call__(self, spec, task_state):
        source_data : BC.BookmarkCollection      = FROM_KEY.to_any(spec, task_state, type_=BC.BookmarkCollection)

        pre_count = len(source_data)
        source_data.merge_duplicates()
        post_count = len(source_data)
        printer.info("Merged %s entries", pre_count - post_count)

"""


"""
