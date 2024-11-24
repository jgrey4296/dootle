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
import re
import time
import types
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import networkx as nx

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# ##-- stdlib imports
from collections import defaultdict

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import doot.errors
from doot._abstract import (FailPolicy_p, Job_i, Task_i, TaskBase_i,
                            TaskRunner_i, TaskTracker_i)
from doot.control.tracker import DootTracker, _TrackerEdgeType
from doot.structs import TaskArtifact, TaskName, TaskSpec
from doot.task.base_task import DootTask

# ##-- end 3rd party imports

STORAGE_FILE : Final[pl.Path] = doot.config.on_fail(DootKey.build(".tasks.bk")).settings.general.tracker_file(wrapper=DootKey.build).to_path()

@doot.check_protocol
class DootDateTracker(DootTracker):
    """
      Track task status, using file product modification times
      reads and writes modification times to wherever config.settings.general.tracker_file locates

    """

    def __init__(self, shadowing:bool=False, *, policy=None):
        super().__init__(shadowing=shadowing, policy=policy)
        self._modification_db = None

    def write(self, target:pl.Path) -> None:
        """ Write the dependency graph to a file """
        # STORAGE_FILE.write_text(str(self._modification_db))
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        """ Read the dependency graph from a file """
        # self._modification_db = STORAGE_FILE.read_text()
        raise NotImplementedError()

    def update_state(self, task:str|TaskBase_i|TaskArtifact|TaskName, state:self.state_e):
        now = datetime.datetime.now()
        match state:
            case self.state_e.EXISTS:
                task_date  = self._modification_db.set(str(task), now)
                self._invalidate_descendents(task)
                pass
            case self.state_e.FAILED:
                self._invalidate_descendents(task)
                pass
            case self.state_e.SUCCESS:
                pass

    def _invalidate_descendents(task):
        incomplete, descendants = self._task_dependents(task)
        pass
