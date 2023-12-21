#!/usr/bin/env python3
"""

"""
##-- default imports
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

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import doot
from doot._abstract import Command_i
from doot.structs import TaskStub
from collections import defaultdict

##-- data
data_path = doot.constants.TOML_TEMPLATE
##-- end data

class ExampleCmd(Command_i):
    """
      For checking doot finds system installed entry points
    """
    _name      = "example"
    _help      = [ "An Example Plugin Cmd" ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + []

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        printer.info("This is an Example Cmd edited")
