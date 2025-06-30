#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
# ruff: noqa: N812
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import typing
import weakref
from importlib.metadata import EntryPoint
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv._abstract.protocols import (Buildable_p, SpecStruct_p)
from jgdv._abstract.pydantic_proto import ProtocolModelMeta
from jgdv.cli import ParamSpec, ParamSpecMaker_m
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import Location
from jgdv.structs.strang import CodeReference
import jgdv.structs.strang.errors as StrangErrs
import doot
import doot.errors
# ##-- end 3rd party imports

from doot.util._interface import TaskFactory_p, SubTaskFactory_p
from doot.util.factory import TaskFactory, SubTaskFactory
from doot.workflow import _interface as API
from doot.workflow._interface import TaskSpec_i, Task_p, Job_p, Task_i, TaskMeta_e, RelationMeta_e, TaskName_p
from doot.workflow import ActionSpec, InjectSpec, TaskArtifact, RelationSpec, TaskName, TaskSpec, DootTask, DootJob
from .task import FSMTask, FSMJob

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Any, Annotated, override
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, overload
from dataclasses import _MISSING_TYPE, InitVar, dataclass, field, fields
from pydantic import (BaseModel, BeforeValidator, Field, ValidationError,
                      ValidationInfo, ValidatorFunctionWrapHandler, ConfigDict,
                      WrapValidator, field_validator, model_validator)

if TYPE_CHECKING:
    from jgdv import Maybe
    import enum
    from typing import Final
    from typing import ClassVar, LiteralString
    from typing import Never, Self, Literal, _SpecialType
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    type SpecialType = _SpecialType

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##--| Consts
DEFAULT_ALIAS     : Final[str]             = doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS
DEFAULT_BLOCKING  : Final[tuple[str, ...]] = ("required_for", "on_fail")
DEFAULT_RELATION   : Final[RelationMeta_e] = RelationMeta_e.default()
##--| Utils

##--|

@Proto(TaskFactory_p)
class FSMFactory(TaskFactory):
    """
    Factory to create task specs, instantiate them, and make tasks
    """
    def __init__(self, *, spec_ctor:Maybe[type]=None, task_ctor:Maybe[type]=None, job_ctor:Maybe[type]=None):
        super().__init__(spec_ctor=spec_ctor,
                         task_ctor=task_ctor or FSMTask,
                         job_ctor=job_ctor or FSMJob)


@Proto(SubTaskFactory_p)
class FSMSubFactory(SubTaskFactory):
    """Additional utilities mixin for job based task specs"""
    pass
