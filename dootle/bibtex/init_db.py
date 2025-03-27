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
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKey, DKeyed
import bibtexparser as b
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares import BlockMiddleware
from bibtexparser.middlewares.middleware import BlockMiddleware
import doot
from doot._abstract.task import Action_p

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
class BibtexInitAction:
    """
      Initialise a bibtex database.
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
                ctor = b.Library
            case CodeReference:
                ctor = (db_base.safe_import() or b.Library)

        db = ctor()
        doot.report.trace("Bibtex Database Initialised")
        return { _update : db }
