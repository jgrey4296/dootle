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

##-- 3rd party imports
import bibtexparser as b
import bibtexparser.model as model
import doot
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware
from doot._abstract.task import Action_p
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class BibtexFailedBlocksWriteAction(Action_p):
    """ A reporter of blocks that failed to parse """

    @DKeyed.formats("failed_blocks")
    @DKeyed.paths("target")
    def __call__(self, spec, state, failed_blocks, target):
        if not bool(failed_blocks):
            return

        with open(target, 'w') as f:
            for block in failed_blocks:
                f.write(block.raw)
