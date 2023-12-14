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
printer = logmod.getLogger("doot._printer")

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
            if not ("file" in field.key or "look_in" in field.key):
                continue

            base = pl.Path(field.value)
            match base.parts[0]:
                case "/":
                    field.value = base
                case "~":
                    field.value = base.expanduser().absolute()
                case _:
                    field.value = self._lib_root / base

            if not field.value.exists():
                printer.warning("On Import file does not exist: %s", field.value)

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
                    if not field.value.exists():
                        printer.warning("On Export file does not exist: %s", field.value)
                    field.value = str(field.value.relative_to(self._lib_root))
                elif "look_in" in field.key:
                    field.value = str(field.value.relative_to(self._lib_root))
            except ValueError:
                field.value = str(field.value)


        return entry

"""

"""



class MergeLastNameFirstName(ms.MergeNameParts):
    """Middleware to merge a persons name parts (first, von, last, jr) into a single string.

    Name fields (e.g. author, editor, translator) are expected to be lists of NameParts.
    """

    # docstr-coverage: inherited
    @staticmethod
    def metadata_key() -> str:
        return "dootle_merge_name_parts"

    def _transform_field_value(self, name) -> List[str]:
        if not isinstance(name, list) and all(isinstance(n, NameParts) for n in name):
            raise ValueError("Expected a list of NameParts, got {}. ".format(name))

        return [self._merge_name(n) for n in name]

    def _merge_name(self, name):
        result = []

        if name.von:
            result.append(" ".join(name.von))
            result.append(" ")

        if name.last:
            result.append(" ".join(name.last))
            result.append(", ")

        if name.jr:
            result.append(" ".join(name.jr))
            result.append(", ")

        result.append(" ".join(name.first))


        return "".join(result).removesuffix(", ")



class FieldAwareLatexEncodingMiddleware(ms.LatexEncodingMiddleware):
    """Latex-Encodes all strings in the library"""
    _skip_fields = ["url", "file", "doi", "crossref"]

    def metadata_key(self) -> str:
        return "field_aware_latex_encoding"

    def transform_entry(self, entry: Entry, library: Library) -> Block:
        errors = []
        for field in entry.fields:
            if any(x in field.key for x in self._skip_fields):
                continue
            if isinstance(field.value, str):
                field.value, e = self._transform_python_value_string(field.value)
                errors.append(e)
            elif isinstance(field.value, ms.NameParts):
                field.value.first = self._transform_all_strings(
                    field.value.first, errors
                )
                field.value.last = self._transform_all_strings(field.value.last, errors)
                field.value.von = self._transform_all_strings(field.value.von, errors)
                field.value.jr = self._transform_all_strings(field.value.jr, errors)
            else:
                logging.info(
                    f" [{self.metadata_key()}] Cannot python-str transform field {field.key}"
                    f" with value type {type(field.value)}"
                )

        errors = [e for e in errors if e != ""]
        if len(errors) > 0:
            errors = ms.PartialMiddlewareException(errors)
            return ms.MiddlewareErrorBlock(block=entry, error=errors)
        else:
            return entry

class FieldAwareLatexDecodingMiddleware(ms.LatexDecodingMiddleware):
    """Latex-Encodes all strings in the library"""
    _skip_fields = ["url", "file", "doi", "crossref"]

    def metadata_key(self) -> str:
        return "field_aware_latex_decoding"

    def transform_entry(self, entry: Entry, library: Library) -> Block:
        errors = []
        for field in entry.fields:
            if any(x in field.key for x in self._skip_fields):
                continue
            if isinstance(field.value, str):
                field.value, e = self._transform_python_value_string(field.value)
                errors.append(e)
            elif isinstance(field.value, ms.NameParts):
                field.value.first = self._transform_all_strings(
                    field.value.first, errors
                )
                field.value.last = self._transform_all_strings(field.value.last, errors)
                field.value.von = self._transform_all_strings(field.value.von, errors)
                field.value.jr = self._transform_all_strings(field.value.jr, errors)
            else:
                logging.info(
                    f" [{self.metadata_key()}] Cannot python-str transform field {field.key}"
                    f" with value type {type(field.value)}"
                )

        errors = [e for e in errors if e != ""]
        if len(errors) > 0:
            errors = ms.PartialMiddlewareException(errors)
            return ms.MiddlewareErrorBlock(block=entry, error=errors)
        else:
            return entry



class TitleStripMiddleware(BlockMiddleware):
    """
      Convert file paths in bibliography to pl.Path's, expanding relative paths according to lib_root
    """

    @staticmethod
    def metadata_key():
        return "jg-title-strip"

    def __init__(self, lib_root:pl.Path=None):
        super().__init__(True, True)
        self._lib_root = lib_root

    def transform_entry(self, entry, library):
        for field in entry.fields:
            if not "title" in field.key:
                continue

            field.value = field.value.strip()

        return entry
