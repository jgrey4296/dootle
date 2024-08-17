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
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import bibtexparser as b
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware

import doot
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed

DB_KEY      : Final[DKey] = DKey("bib_db", implicit=True)

class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a state database, in place.

      addFn to state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """

    @DKeyed.redirects("year_")
    @DKeyed.redirects("from", multi=True, re_mark=DKey.mark.PATH)
    @DKeyed.types("parse_stack", check=list)
    @DKeyed.types("update", check=b.Library|None)
    def __call__(self, spec, state, _year, from_ex, parse_stack, _update):
        year_key    = _year
        db          = _update or DB_KEY.expand(spec, state)
        file_list   = [x.expand(spec, state) for x in from_ex]
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
