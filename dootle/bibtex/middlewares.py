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

import bibtexparser
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware

# BlockMiddleware - subclass for working on blocks
# LibraryMiddleware - subclass for library wide transformations

# TODO ideal stemmer
# TODO library location enforcer
# TODO field lowercaser
# TODO year checker
# TODO title split
# TODO output name formatting
# TODO ISBN formatting
# TODO pdf metadata application
# TODO Url way-backer

# TODO reporters - author/editor counts, year entries, types, entries with files


class ParsePathsMiddleware(BlockMiddleware):
    """
      Convert file paths in bibliography to pl.Path's, expanding relative paths according to lib_root
    """

    @staticmethod
    def metadata_key():
        return "jg-paths-in"

    def __init__(self, lib_root:pl.Path=None):
        super().__init__(True, True)
        self._lib_root = lib_root

    def transform_entry(self, entry, library):
        for field in entry.fields:
            if "file" in field.key or "look_in" in field.key:
                base = pl.Path(field.value)
                match base.parts[0]:
                    case "/":
                        field.value = base
                    case "~":
                        field.value = base.expanduser().absolute()
                    case _:
                        field.value = self._lib_root / base

        return entry

class ParseTagsMiddleware(BlockMiddleware):
    """
      Read Tag strings, split them into a set
    """

    @staticmethod
    def metadata_key():
        return "jg-tags-in"

    def __init__(self):
        super().__init__(True, True)

    def transform_entry(self, entry, library):
        for field in entry.fields:
            if field.key == "tags":
                field.value = field.value.split(",")

        return entry


class WriteTagsMiddleware(BlockMiddleware):
    """
      Reduce tag set to a string
    """

    @staticmethod
    def metadata_key():
        return "jg-tags-out"


    def __init__(self):
        super().__init__(True, True)

    def transform_entry(self, entry, library):
        for field in entry.fields:
            if field.key == "tags":
                field.value = ",".join(field.value)

        return entry

class WritePathsMiddleware(BlockMiddleware):
    """
      Relativize library paths back to strings
    """

    @staticmethod
    def metadata_key():
        return "jg-paths-out"

    def __init__(self, lib_root:pl.Path=None):
        super().__init__(True, True)
        self._lib_root = lib_root

    def transform_entry(self, entry, library):
        for field in entry.fields:
            try:
                if "file" in field.key:
                    field.value = str(field.value.relative_to(self._lib_root))
                elif "look_in" in field.key:
                    field.value = str(field.value.relative_to(self._lib_root))
            except ValueError:
                field.value = str(field.value)


        return entry

"""

"""
