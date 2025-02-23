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
from jgdv import Proto
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.files.bookmarks.collection import BookmarkCollection
import doot
import doot.errors
from doot._abstract import Action_p

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.bookmarks.alchemy_fns import extract as alc_extract
from dootle.bookmarks.pony_fns import extract as pony_extract

# ##-- end 1st party imports

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

@Proto(Action_p)
class BookmarksPonyExtraction:
    """
      extract bookmarks from a sqlite firefox db using pony
    """

    @DKeyed.paths("from")
    @DKeyed.types("debug", fallback=False)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, debug, _update):
        db_loc         = _from
        try:
            printer.info("Starting Extraction")
            result       = pony_extract(db_loc, debug=debug)
            printer.info("Extraction Complete: %s results", len(result))
            return { _update : result }
        except Exception as err:
            raise doot.errors.ActionError("Pony Errored: %s", str(err)) from err

@Proto(Action_p)
class BookmarksAlchemyExtraction:
    """
      extract bookmarks from a sqlite firefox db using pony
    """

    @DKeyed.paths("from")
    @DKeyed.types("debug", fallback=False)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, debug, _update):
        db_loc         = _from
        try:
            printer.info("Starting Extraction")
            result       = alc_extract(db_loc, debug=debug)
            printer.info("Extraction Complete: %s results", len(result))
            return { _update : result }
        except Exception as err:
            raise doot.errors.ActionError("Pony Errored: %s", str(err)) from err

@Proto(Action_p)
class BookmarksLoad:

    @DKeyed.paths("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        load_path = _from
        data_key  = _update
        printer.info("Loading Bookmarks from: %s", load_path)
        result    = BookmarkCollection.read(load_path)
        printer.info("Loaded %s Bookmarks", len(result))
        return { data_key : result }

@Proto(Action_p)
class BookmarksMerge:

    @DKeyed.redirects("from", multi=True)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        source_keys   : list[DKey]                  = _from
        source_values : list                        = [y for x in source_keys for y in x.expand(spec, state, check=list)]

        merged                                      = BookmarkCollection()
        for x in source_values:
            match x:
                case BookmarkCollection():
                    pre_count = len(merged)
                    merged   += x
                    growth    = len(merged) - pre_count
                    printer.info("Added %s bookmarks, Total Growth: %s", len(x), growth)
                case _:
                    raise doot.errors.ActionError("Unknown type tried to merge into bookmarks", x)

        return { _update : merged }

@Proto(Action_p)
class BookmarksToStr:

    @DKeyed.types("from", check=BookmarkCollection)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        source_data : BookmarkCollection           = _from

        printer.info("Writing Bookmark Collection of size: %s", len(source_data))
        return { _update : str(source_data) }

@Proto(Action_p)
class BookmarksRemoveDuplicates:

    @DKeyed.types("from")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, _update):
        source_data : BookmarkCollection      = _from

        pre_count = len(source_data)
        source_data.merge_duplicates()
        post_count = len(source_data)
        printer.info("Merged %s entries", pre_count - post_count)
