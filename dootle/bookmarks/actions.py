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
from doot.utils.string_expand import expand_str, expand_set, expand_to_obj, expand_key

from dootle.bookmarks.db_fns import extract
from dootle.bookmarks import structs as BC

printer = logmod.getLogger("doot._printer")

class BookmarksPonyExtraction(Action_p):
    """
      extract bookmarks _from a sqlite firefox db using pony
    """
    _toml_kwargs = ["_from", "update_", "debug"]

    def __call__(self, spec, task_state):
        db_loc         = expand_str(spec.kwargs._from, spec, task_state)
        update_key     = expand_str(spec.kwargs.update_, spec, task_state)
        debug          = spec.kwargs.on_fail(False).debug()
        try:
            printer.info("Starting Extraction")
            result       = extract(db_loc, debug=debug)
            printer.info("Extraction Complete: %s results", len(result))
            return { update_key : result }
        except Exception as err:
            raise doot.errors.DootActionError("Pony Errored: %s", str(err)) from err


class BookmarksLoad(Action_p):

    _toml_kwargs = ["_from", "update_"]

    def __call__(self, spec, task_state):
        load_path = expand_str(spec.kwargs._from, spec, task_state)
        data_key  = expand_str(spec.kwargs.update_, spec, task_state)
        printer.info("Loading Bookmarks _from: %s", load_path)
        result    = BC.BookmarkCollection.read(load_path)
        printer.info("Loaded %s Bookmarks", len(result))
        return { data_key : result }

class BookmarksMerge(Action_p):

    _toml_kwargs = ["from_", "update_"]

    def __call__(self, spec, task_state):
        data_key                                 = expand_str(spec.kwargs.update_, spec, task_state)
        source_data : set[BC.BookmarkCollection] = expand_set(spec.kwargs.from_, spec, task_state)

        merged = BC.BookmarkCollection()
        for x in source_data:
            pre_count = len(merged)
            merged += x
            growth = len(merged) - pre_count
            printer.info("Added %s bookmarks, Total Growth: %s", len(x), growth)

        return { data_key : merged }

class BookmarksToStr(Action_p):
    _toml_kwargs = ["update_", "from_"]

    def __call__(self, spec, task_state):
        data_key                                      = expand_str(spec.kwargs.update_, spec, task_state)
        source_data : set[BC.BookmarkCollection]      = expand_to_obj(spec.kwargs.from_, spec, task_state)

        printer.info("Writing Bookmark Collection of size: %s", len(source_data))
        return { data_key : str(source_data) }


class BookmarksRemoveDuplicates(Action_p):
    _toml_kwargs = ["from_"]

    def __call__(self, spec, task_state):
        source_data : BC.BookmarkCollection      = expand_to_obj(spec.kwargs.from_, spec, task_state)

        pre_count = len(source_data)
        source_data.merge_duplicates()
        post_count = len(source_data)
        printer.info("Merged %s entries", pre_count - post_count)

"""


"""
