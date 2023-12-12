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
import doot.utils.expansion as exp
from dootle.bibtex import middlewares as dmids

NEWLINE_RE                 : Final[re.Pattern] = re.compile(r"\n+\s*")

default_convert_exclusions : Final[list]       = ["file", "url", "ID", "ENTRYTYPE", "_FROM_CROSSREF", "doi", "crossref", "tags", "look_in", "note", "reference_number", "see_also"]
convert_exclusions         : Final[list]       = doot.config.on_fail(default_convert_exclusions, list).bibtex.convert_exclusions()

DB_KEY                     : Final[str] = "bib_db"
STATE_KEY                  : Final[str] = "load_key"
TEXT_KEY                   : Final[str] = "bib_text"
YEAR_KEY                   : Final[str] = "current_year"

class BibtexInitAction(Action_p):
    """
      Initialise a bibtex database. Override '_entry_transform' for customisation of loading.

      pass a callable as the spec.args value to use instead of _entry_transform
    """
    _toml_kwargs = ["update_"]

    def __call__(self, spec, task_state:dict):
        data_key = exp.to_str(spec.kwargs.on_fail(DB_KEY).update_(), spec, task_state)
        if data_key in task_state:
            return True

        db                   = b.Library()
        printer.info("Bibtex Database Initialised")
        return { data_key : db }

class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a task_state database, in place.

      addFn to task_state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """
    _toml_kwargs = ["update_", "crossref", "parse_stack", "_from"]

    def __call__(self, spec, task_state:dict):
            year_key             = exp.to_str(spec.kwargs.on_fail(YEAR_KEY).year_(), spec, task_state, indirect=True)
            db                   = exp.to_any(spec.kwargs.on_fail(DB_KEY).update_(), spec, task_state, indirect=True)
            from_val             = exp.to_any(spec.kwargs.on_fail("_from").from_(), spec, task_state, indirect=True)
            match from_val:
                case str():
                    file_list    = [exp.to_path(from_str, spec, task_state)]
                case pl.Path():
                    file_list    = [from_val]
                case list():
                    file_list    = [exp.to_path(x, spec, state) for x in from_val]

            parse_stack          = exp.to_any(spec.kwargs.on_fail("parse_stack").parse_stack_(), spec, task_state, indirect=True)


            printer.info("Attempting to load files: %s", [str(x) for x in file_list])
            for loc in file_list:
                printer.info("Loading bibtex: %s", loc)
                try:
                    lib  = b.parse_file(loc, parse_stack=parse_stack)
                    db.add(lib.entries)
                    printer.info("Loaded: %s entries",  len(lib.entries))
                    failed = lib.failed_blocks
                    if bool(failed):
                        printer.warn("Parse Failure: %s Blocks Failed in %s", len(failed), loc)
                        lib.add(failed)
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
                return { year_key: loc.stem }

            return True


class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """
    _toml_kwargs = ["from_", "update_", "write_stack", "format"]

    def __call__(self, spec, task_state):
        data_key                                = exp.to_str(spec.kwargs.on_fail(TEXT_KEY).update_(), spec, task_state)
        db                                      = exp.to_any(spec.kwargs.on_fail(DB_KEY).from_(), spec, task_state, indirect=True)
        write_stack                             = exp.to_any(spec.kwargs.on_fail("write_stack").write_stack_(), spec, task_state, indirect=True)
        format                                  = exp.to_any(spec.kwargs.on_fail("format").format_(), spec, task_state, indirect=True)

        if format is None:
            format                              = b.BibtexFormat()
            format.value_column                 = 15
            format.indent                       = " "
            format.block_separator              = "\n"
            format.trailing_comma               = True

        result                                  = b.write_string(db, unparse_stack=write_stack, bibtex_format=format)
        return { data_key : result }

# TODO library merge - lib.add(entries)

"""

"""
