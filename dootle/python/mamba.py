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
import os
import pathlib as pl
import re
import time
import types
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors
import sh
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

class MambaEnv:
    """ Set up a mamba env to use

    returns a baked command to pass to the normal shell action in env
    """

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
