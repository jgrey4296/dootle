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

# ##-- 2rd party imports
from jgdv import Proto, Maybe
from jgdv.structs.dkey import DKey, DKeyed
import bibtexparser as b
from bibtexparser import Library
import doot
from bibtexparser import middlewares as ms
from bibtexparser import model
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p

# ##-- end 3rd party imports

# ##-- 1st party imports
from ._interface import DB_KEY

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
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from dootle.structs import ActionSpec

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Action_p)
class BibtexFailedBlocksWriteAction:
    """ extract failed blocks from the library to task state """

    @DKeyed.types("from", check=Library|None)
    @DKeyed.paths("to", fallback=None)
    @DKeyed.redirects("update_", fallback=None)
    def __call__(self, spec:ActionSpec, state:dict, _from:Maybe[Library], _to:Maybe[pl.Path], _update:str):
        match _from or DKey(DB_KEY).expand(spec, state):
            case None:
                raise ValueError("No bib database found")
            case b.Library() as db:
                pass

        match db.failed_blocks:
            case []:
                return
            case [*xs] if isinstance(_to, pl.Path):
                with _to.open('w') as f:
                    for block in xs:
                        f.write(block.raw)
            case [*xs] if _update is not None:
                return { _update : list(xs) }
