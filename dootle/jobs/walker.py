#!/usr/bin/env python3
"""

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
import random
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
from jgdv import Proto, Mixin
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors
from doot._abstract import Action_p
from doot.actions.core.action import DootBaseAction
from doot.mixins.path_manip import Walker_m
from doot.structs import TaskName, TaskSpec
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Action_p)
@Mixin(Walker_m)
class JobWalkAction(DootBaseAction):
    """
      Triggers a directory walk to build tasks from

      starts at each element in `roots`,
      files must match with a suffix in `exts`, if bool(exts)
      potential files are used that pass `fn`,

    registered as job.walk

    """

    @DKeyed.types("roots", "exts")
    @DKeyed.types("recursive", check=bool|None, fallback=False)
    @DKeyed.references("fn")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, fn, _update):
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        rec     = recursive or False
        roots   = [DKey(x, mark=DKey.Mark.PATH).expand(spec, state) for x in roots]
        match fn:
            case CodeReference():
                match fn():
                    case ImportError() as err:
                        raise err
                    case x:
                        accept_fn = x
            case None:
                def accept_fn(x):
                    return True

        results = [x for x in self.walk_all(roots, exts, rec=rec, fn=accept_fn)]
        return { _update : results }
