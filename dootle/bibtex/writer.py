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
import bibtexparser as b
from bibtexparser import model
import doot
from bibble.io import Writer
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
from dootle.bibtex import DB_KEY

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

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
printer = doot.subprinter()
##-- end logging

@Proto(Action_p)
class BibtexToStrAction:
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

@Proto(Action_p)
class BibtexBuildWriter:

    @DKeyed.references("stack")
    @DKeyed.references("class", fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, stack, _class, _update):
        fn    = stack()
        stack = fn(spec, state)

        match _class:
            case CodeReference():
                writer_type = _class()
                writer      = writer_type(stack)
            case None:
                writer = Writer(stack)


        return { _update : writer }
