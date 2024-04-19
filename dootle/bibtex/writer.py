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
from doot.structs import DootKey

DB_KEY      : Final[DootKey] = DootKey.build("bib_db")

class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """

    @DootKey.dec.types("from", hint={"type_":b.library.Library|None, "chain":[DB_KEY]})
    @DootKey.dec.types("write_stack", hint={"type_":list})
    @DootKey.dec.types("bib_format", hint={"type_": b.BibtexFormat|None})
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, _from, write_stack, bib_format, _update):
        db          = _from
        if bib_format is None:
            bib_format                              = b.BibtexFormat()
            bib_format.value_column                 = 15
            bib_format.indent                       = " "
            bib_format.block_separator              = "\n"
            bib_format.trailing_comma               = True

        result = b.write_string(db, unparse_stack=write_stack, bibtex_format=bib_format)
        return { _update : result }
