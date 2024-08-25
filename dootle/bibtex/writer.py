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
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

DB_KEY      : Final[DKey] = DKey("bib_db", implicit=True)

class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """

    @DKeyed.types("from", check=b.library.Library|None)
    @DKeyed.types("write_stack", check=list)
    @DKeyed.types("bib_format", check=b.BibtexFormat|None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, write_stack, bib_format, _update):
        db          = _from or DKey(DB_KEY).expand(spec, state)
        if bib_format is None:
            bib_format                              = b.BibtexFormat()
            bib_format.value_column                 = 15
            bib_format.indent                       = " "
            bib_format.block_separator              = "\n"
            bib_format.trailing_comma               = True

        result = b.write_string(db, unparse_stack=write_stack, bibtex_format=bib_format)
        return { _update : result }
