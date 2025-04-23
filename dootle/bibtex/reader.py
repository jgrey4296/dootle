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
from jgdv.structs.strang import CodeReference
import bibtexparser as b
from bibble import PairStack
from bibble.io import Reader
from bibtexparser import model
import doot
from doot._abstract.task import Action_p

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.bibtex._interface import DB_KEY

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
##-- end logging

@Proto(Action_p)
class BibtexReadAction:
    """ Parse all the bibtext files into a state database, in place.

      addFn to state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """

    @DKeyed.redirects("year_")
    @DKeyed.types("from")
    @DKeyed.types("reader", check=Reader)
    @DKeyed.types("update", check=b.Library|None)
    def __call__(self, spec, state, _year, _from, reader, _update):
        year_key    = _year
        results     = {}
        match _from:
            case pl.Path() as x:
                file_list = [x]
            case str():
                _from = [DKey(_from, mark=DKey.Mark.PATH)]
                file_list   = [x.expand(spec, state) for x in _from]
            case [*xs]:
                _from = [DKey(x, mark=DKey.Mark.PATH) for x in xs]
                file_list   = [x.expand(spec, state) for x in _from]
            case x:
                raise TypeError(type(x))

        match _update or DB_KEY.expand(spec, state):
            case None:
                db = b.Library()
                results[DB_KEY] = db
            case b.Library() as x:
                db = x

        doot.report.detail("Starting to load %s files", len(file_list))
        for loc in file_list:
            doot.report.trace("Loading bibtex: %s", loc)
            try:
                filelib = reader.read(loc, into=db)
                doot.report.trace("Loaded: %s entries",  len(filelib.entries))
            except OSError as err:
                doot.report.error("Bibtex File Loading Errored: %s : %s", loc, err)
                return False

        doot.report.trace("Total DB Entry Count: %s", len(db.entries))
        if len(file_list) == 1:
            loc = file_list[0]
            doot.report.trace("Current year: %s", loc.stem)
            results.update({ year_key: loc.stem })

        return results

@Proto(Action_p)
class BibtexBuildReader:
    """
    Build a bibtex reader object, with a given parse stack.
    """

    @DKeyed.references("db_base", "class")
    @DKeyed.types("stack", check=PairStack)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, db_base, _class, stack, _update):
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
