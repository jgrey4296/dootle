#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import sh
import doot
import doot.errors
from doot.structs import DootKey
from doot._abstract import Action_p

FROM         = DootKey.make("from")
TO           = DootKey.make("to")
EXT          = DootKey.make("ext")

plant_ext    = doot.config.on_fail("png", str).plantuml.ext()

def run_plantuml(spec, state):
    ext    = EXT.expand(spec, state)
    source = FROM.to_path(spec, state)
    dest   = TO.to_path(spec, state)
    sh.plantuml(f"-t{ext}", "-output", dest.parent, "-filename", dest.stem, source)
    return



def check_plantuml(spec, state):
    source = FROM.to_path(spec, state)
    sh.plantuml("-checkonly", source)
    return
