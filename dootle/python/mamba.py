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
import os
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
import doot
import doot.errors
import sh
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()

##-- end logging

class MambaEnv:
    """ Set up a mamba env to use, returns a baked command to pass to the normal shell action in shenv_ """

    @DKeyed.types("env", check=list|str)
    @DKeyed.redirects("update_", fallback=None)
    def __call__(self, spec, state, _env, _update):
        if _update is None:
            raise ValueError("Using a mamba env requires an update target")
        
        match _env:
            case [x]:
                env = x
            case str() as x:
                env = x
        sh_ctxt = sh.mamba.bake("run", "-n", env, _return_cmd=True, _tty_out=False)
        return { _update : sh_ctxt }
