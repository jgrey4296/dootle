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

import bibtexparser as b
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware

import doot
from doot._abstract.task import Action_p
from doot.structs import DootKey

NEWLINE_RE                 : Final[re.Pattern] = re.compile(r"\n+\s*")

default_convert_exclusions : Final[list]       = ["file", "url", "ID", "ENTRYTYPE", "_FROM_CROSSREF", "doi", "crossref", "tags", "look_in", "note", "reference_number", "see_also"]
convert_exclusions         : Final[list]       = doot.config.on_fail(default_convert_exclusions, list).bibtex.convert_exclusions()

##-- expansion keys
UPDATE      : Final[DootKey] = DootKey.build("update_")
YEAR_KEY    : Final[DootKey] = DootKey.build("year_")
PARSE_STACK : Final[DootKey] = DootKey.build("parse_stack")
WRITE_STACK : Final[DootKey] = DootKey.build("write_stack")
FROM_KEY    : Final[DootKey] = DootKey.build("from")
DB_KEY      : Final[DootKey] = DootKey.build("bib_db")
FORMAT_KEY  : Final[DootKey] = DootKey.build("bib_format")

##-- end expansion keys

# TODO library merge - lib.add(entries)

class BibtexInitAction(Action_p):
    """
      Initialise a bibtex database. Override '_entry_transform' for customisation of loading.

      pass a callable as the spec.args value to use instead of _entry_transform
    """
    _toml_kwargs = [UPDATE]

    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _update):
        data_key = _update
        if data_key in state:
            return True

        db                   = b.Library()
        db.source_files      = set()
        printer.info("Bibtex Database Initialised")
        return { data_key : db }

class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a state database, in place.

      addFn to state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """
    _toml_kwargs = [UPDATE, PARSE_STACK, FROM_KEY, YEAR_KEY, "crossref"]

    @DootKey.kwrap.redirects("year_")
    @DootKey.kwrap.redirects_many("from")
    @DootKey.kwrap.types("parse_stack", hint={"type_":list})
    @DootKey.kwrap.types("update_", hint={"type_":b.Library|None, "chain":[DB_KEY]})
    def __call__(self, spec, state, _year, from_ex, parse_stack, _update):
        year_key    = _year
        db          = _update
        file_list   = [x.to_path(spec, state) for x in from_ex]
        results     = {}

        printer.debug("Starting to load %s files", len(file_list))
        for loc in file_list:
            printer.info("Loading bibtex: %s", loc)
            try:
                lib  = b.parse_file(loc, parse_stack=parse_stack)
                db.add(lib.entries)
                db.source_files.add(loc)
                printer.info("Loaded: %s entries",  len(lib.entries))

                if bool(lib.failed_blocks):
                    failed = lib.failed_blocks.copy()
                    results.update({"failed_blocks": failed})
                    printer.warning("Parse Failures have been added to task state['failed_blocks']")

            except UnicodeDecodeError as err:
                printer.error("Unicode Error in File: %s, Start: %s", loc, err.start)
                return False
            except Exception as err:
                printer.error("Bibtex File Loading Errored: %s : %s", loc, err)
                return False

        printer.info("Total DB Entry Count: %s", len(db.entries))
        if len(file_list) == 1:
            loc = doot.locs[file_list[0]]
            printer.info("Current year: %s", loc.stem)
            results.update({ year_key: loc.stem })

        return results

class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """
    _toml_kwargs = [FROM_KEY, UPDATE, WRITE_STACK, FORMAT_KEY]

    @DootKey.kwrap.types("from", hint={"type_":b.library.Library|None, "chain":[DB_KEY]})
    @DootKey.kwrap.types("write_stack", hint={"type_":list})
    @DootKey.kwrap.types("bib_format", hint={"type_": b.BibtexFormat|None})
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, write_stack, bib_format, _update):
        data_key    = _update
        db          = _from
        if bib_format is None:
            bib_format                              = b.BibtexFormat()
            bib_format.value_column                 = 15
            bib_format.indent                       = " "
            bib_format.block_separator              = "\n"
            bib_format.trailing_comma               = True

        result                                  = b.write_string(db, unparse_stack=write_stack, bibtex_format=bib_format)
        return { data_key : result }

class BibtexFailedBlocksWriteAction(Action_p):

    def __call__(self, spec, state):
        if "failed_blocks" not in state:
            return

        target = DootKey.build("target").to_path(spec, state)
        blocks = state['failed_blocks']
        with open(target, 'w') as f:
            for block in blocks:
                f.write(block.raw)
