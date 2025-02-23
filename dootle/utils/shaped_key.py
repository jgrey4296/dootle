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
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.dkey import SingleDKey
import doot
import numpy as np
from jgdv import identity_fn

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

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class NPShapeDKey(SingleDKey["np"], conv="n", multi=False):
    """ Utility DKey to get a numpy array and validate its shape,

      shape : str. A symbolic description of the expected shape of the array.
      eg: (5,2x,x). ensures a 3d array, with 5 planes, and twice as many rows as columns
    """
    _extra_kwargs = set(["shape"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._typecheck       = np.ndarray
        self._expansion_type  = np.ndarray
        match kwargs.get("shape", None):
            case tuple() | list()  as xs:
                self._shape = tuple(xs)
            case None:
                self._shape = None
            case x:
                raise TypeError("Unrecognized shape format", x)

    def exp_check_result(self, val, opts) -> None:
        """ Checks the shape of the arr matches self._shape """
        match val:
            case DKey.ExpInst(val=np.ndarray()) if self._shape is None:
                pass
            case DKey.ExpInst(val=np.ndarray() as x) if x.shape == self._shape:
                pass
            case DKey.ExpInst(np.ndarray() as x):
                raise ValueError("Expected an array of shape", x.shape, self._shape)
            case x:
                raise ValueError("Expected an array", x)
