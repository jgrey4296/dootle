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
import bibtexparser.model as model
import doot
from bibtexparser import middlewares as ms
from bibtexparser.middlewares import BlockMiddleware
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p
from jgdv.structs.strang import CodeReference
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

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
class BibtexInitAction:
    """
      Initialise a bibtex database. Override '_entry_transform' for customisation of loading.

      pass a callable as the spec.args value to use instead of _entry_transform
    """

    @DKeyed.references("db_base", fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, db_base, _update):
        match _update.expand(spec, state, fallback=None):
            case None:
                pass
            case b.Library():
                return True
            case x:
                raise TypeError("A non-bibtex library is in the field", _update, type(x))

        match db_base:
            case None:
                db = b.Library()
            case CodeReference:
                db = (db_base.safe_import() or b.Library)()

        printer.info("Bibtex Database Initialised")
        return { _update : db }
