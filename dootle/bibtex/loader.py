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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import bibtexparser as b
import doot
from bibble.io import Reader
from bibtexparser import middlewares as ms
from bibtexparser import model
from bibtexparser.middlewares.middleware import BlockMiddleware, Middleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.bibtex import DB_KEY

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a state database, in place.

      addFn to state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """

    @DKeyed.redirects("year_")
    @DKeyed.redirects("from", multi=True, re_mark=DKey.mark.PATH)
    @DKeyed.types("reader", check=Reader)
    @DKeyed.types("update", check=b.Library|None)
    def __call__(self, spec, state, _year, _from, reader, _update):
        year_key    = _year
        file_list   = [x.expand(spec, state) for x in _from]
        results     = {}
        match _update or DB_KEY.expand(spec, state):
            case None:
                db = b.Library()
                results[DB_KEY] = db
            case b.Library() as x:
                db = x

        printer.debug("Starting to load %s files", len(file_list))
        for loc in file_list:
            printer.info("Loading bibtex: %s", loc)
            try:
                filelib = reader.read(loc, into=db)
                printer.info("Loaded: %s entries",  len(filelib.entries))
            except Exception as err:
                printer.error("Bibtex File Loading Errored: %s : %s", loc, err)
                return False

        printer.info("Total DB Entry Count: %s", len(db.entries))
        if len(file_list) == 1:
            loc = file_list[0]
            printer.info("Current year: %s", loc.stem)
            results.update({ year_key: loc.stem })

        return results

class BibtexBuildReader(Action_p):

    @DKeyed.references("stack", "db_base", "class")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, stack, db_base, _class, _update):
        fn = stack()
        stack = fn(spec, state)
        match db_base:
            case CodeReference():
                db_base = db_base()
            case _:
                pass

        match _class:
            case CodeReference():
                reader_type = _class()
                reader = reader_type(stack, lib_base=db_base)
            case None:
                reader = Reader(stack, lib_base=db_base)

        return { _update : reader }
