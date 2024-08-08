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
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
from doot.structs import DKey, DKeyed
import sh
import os

class MambaEnv:
    """ Set up a mamba env to use, returns a baked command to pass to the normal shell action in shenv_ """

    @DKeyed.types("env", check=list|str)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, env, _update):
        match env:
            case [x]:
                env = x
            case str() as x:
                env = x
        sh_ctxt = sh.mamba.bake("run", "-n", env, _return_cmd=True, _tty_out=False)
        return { _update : sh_ctxt }
