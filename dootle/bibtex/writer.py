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
import bibtexparser.model as model
import doot
from bibble.io import Writer
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed
from jgdv.structs.code_ref import CodeReference

# ##-- end 3rd party imports

from dootle.bibtex import DB_KEY

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """

    @DKeyed.types("from", check=b.library.Library|None)
    @DKeyed.types("writer", check=Writer)
    @DKeyed.paths("to", fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _from, writer, _target, _update):
        match _from or DKey(DB_KEY).expand(spec, state):
            case None:
                raise ValueError("No bib database found")
            case b.Library() as db:
                result      = writer.write(db, file=_target)
                return { _update : result }

class BibtexBuildWriter(Action_p):

    @DKeyed.references("stack")
    @DKeyed.references("class", fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, stack, _class, _update):
        fn    = stack.try_import()
        stack = fn(spec, state)

        match _class:
            case CodeReference():
                writer_type = _class.try_import()
                writer = _writer_type(stack)
            case None:
                writer = Writer(stack)


        return { _update : writer }
