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

import bibtexparser as b
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares import BlockMiddleware
from bib_middleware import BibMiddlewareLibrary
from jgdv.structs.code_ref import CodeReference

import doot
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed

class BibtexInitAction(Action_p):
    """
      Initialise a bibtex database. Override '_entry_transform' for customisation of loading.

      pass a callable as the spec.args value to use instead of _entry_transform
    """

    @DKeyed.references("db_base", fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, dbclass, _update):
        match _update.expand(spec, state, fallback=None):
            case None:
                pass
            case b.Library():
                return True
            case x:
                raise TypeError("A non-bibtex library is in the field", _update, type(x))

        match dbclass:
            case None:
                db = b.Library()
            case CodeReference:
                db = (dbclass.safe_import() or b.Library)()

        printer.info("Bibtex Database Initialised")
        return { _update : db }
