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
from doot.util.factory import TaskFactory
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
class SubTaskFactory:
    """Additional utilities mixin for job based task specs"""

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName]:
        return list(obj.generated_names)

    def generate_specs(self, obj:TaskSpec_i) -> list[dict]:
        logging.debug("[Generate] : %s (%s)", obj.name, len(obj.generated_names))
        result : list[dict] = []
        if not obj.name.uuid():
            # Non-instanced specs don't generate subspecs
            return result

        needs_job_head = TaskMeta_e.JOB in obj.meta and not obj.name.is_head()
        if needs_job_head:
            # Jobs generate their head
            result += self._gen_job_head(obj)

        if not (needs_job_head or obj.name.is_cleanup()):
            # Normal tasks generate their cleanup
            # TODO shift to just executing the cleanup?
            result += self._gen_cleanup_task(obj)

        obj.generated_names.update([x['name']  for x in result])
        return result

    def _gen_job_head(self,  obj:TaskSpec_i) -> list[dict]:
        """
          Generate a top spec for a job, taking the jobs cleanup actions
          and using them as the head's main action.
          Cleanup relations are turning into the head's dependencies
          Depends on the job, and its reactively queued.

          Equivalent to:
          await job.depends_on()
          await job.setup()
          subtasks = job.actions()
          await subtasks
          job.head()
          await job.cleanup()
        """
        job_head           = obj.name.de_uniq().with_head().to_uniq()
        tasks              = []
        head_section       = self._raw_data_to_specs(obj.extra.on_fail([], list).head_actions(), relation=RelationMeta_e.needs)
        head_dependencies  = [x for x in head_section if isinstance(x, RelationSpec) and x.target != job_head]
        head_actions       = [x for x in head_section if not isinstance(x, RelationSpec)]
        ctor               = obj.extra.on_fail(None).sub_ctor()

        # build $head$
        head : dict        = {
            "name"             : job_head,
            "ctor"             : ctor,
            "sources"          : obj.sources[:] + [obj.name, None],
            "queue_behaviour"  : API.QueueMeta_e.reactive,
            "depends_on"       : [obj.name, *head_dependencies],
            "required_for"     : obj.required_for[:],
            "cleanup"          : obj.cleanup[:],
            "meta"             : (obj.meta | {TaskMeta_e.JOB_HEAD}) - {TaskMeta_e.JOB},
            "actions"          : head_actions,
            **obj.extra,
            }
        assert(TaskMeta_e.JOB not in head['meta'])
        tasks.append(head)
        return tasks

    def _gen_cleanup_task(self, obj:TaskSpec_i) -> list[dict]:
        """ Generate a cleanup task, shifting the 'cleanup' actions and dependencies
          to 'depends_on' and 'actions'
        """
        cleanup_name       = obj.name.de_uniq().with_cleanup().to_uniq()
        base_deps          = [obj.name] + [x for x in obj.cleanup if isinstance(x, RelationSpec) and x.target != cleanup_name]
        actions            = [x for x in obj.cleanup if isinstance(x, ActionSpec)]
        sources            = [obj.name]

        cleanup : dict = {
            "name"             : cleanup_name,
            "ctor"             : obj.ctor,
            "sources"          : sources,
            "queue_behaviour"  : API.QueueMeta_e.reactive,
            "depends_on"       : base_deps,
            "actions"          : actions,
            "cleanup"          : [],
            "meta"             : (obj.meta | {TaskMeta_e.TASK}) - {TaskMeta_e.JOB},
            }
        assert(not bool(cleanup['cleanup']))
        return [cleanup]

    def _raw_data_to_specs(self, deps:list[str|dict], *, relation:RelationMeta_e=DEFAULT_RELATION) -> list[ActionSpec|RelationSpec]:
        """ Convert toml provided raw data (str's, dicts) of specs into ActionSpec and RelationSpec object"""
        results = []
        for x in deps:
            match x:
                case ActionSpec() | RelationSpec():
                    results.append(x)
                case { "do": action  } as d:
                    assert(isinstance(d, dict))
                    results.append(ActionSpec.build(d))
                case _:
                    results.append(RelationSpec.build(x, relation=relation))

        return results
