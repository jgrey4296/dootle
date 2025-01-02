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

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot.structs import DKey
from jgdv.structs.dkey.core import SingleDKey, identity

import numpy as np

class NPShapeDKey(SingleDKey, mark=np.ndarray, tparam="n", multi=False):
    """ Utility DKey to get a numpy array and validate its shape,

      shape : str. A symbolic description of the expected shape of the array.
      eg: (5,2x,x). ensures a 3d array, with 5 planes, and twice as many rows as columns
    """

    def __init__(self, *args, **kwargs):
        assert("shape" in kwargs)
        super().__init__(*args, **kwargs)
        self._typecheck = np.ndarray
        self._shape     : str = kwargs['shape']

    def _check_shape(self, arr) -> bool:
        """ Checks the shape of the arr matches self._shape """
        return False
