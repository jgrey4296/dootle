#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import bibtexparser as b
import bibtexparser.model as model
import doot
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware, Middleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed
from bib_middleware.io import Reader
from jgdv.structs.code_ref import CodeReference

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

DB_KEY      : Final[DKey] = DKey("bib_db", implicit=True)

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

    @DKeyed.types("stack", check=list|CodeReference)
    @DKeyed.types("db_base", check=None|CodeReference|type, fallback=None)
    @DKeyed.types("class", check=None|CodeReference|type)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, stack, db_base, _class, _update):
        match stack:
            case list():
                pass
            case CodeReference():
                fn = stack.try_import()
                stack = fn(spec, state)

        match _class:
            case type():
                reader = _class(stack, lib_base=db_base)
            case None:
                reader = Reader(stack, lib_base=db_base)


        return { _update : reader }
