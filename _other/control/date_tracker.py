#!/usr/bin/env python3
"""

"""
# ruff: noqa: DTZ005
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import re
import time
import types
from collections import defaultdict
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKey
import doot
import doot.errors
import networkx as nx
from doot.control.tracker import DootTracker, _TrackerEdgeType
from doot.task.base_task import DootTask

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
    import pathlib as pl
    from doot.structs import TaskArtifact, TaskName, TaskSpec

##--|
from doot._abstract import (TaskBase_i, TaskRunner_i, TaskTracker_i)
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

STORAGE_FILE : Final[pl.Path] = doot.config.on_fail(DKey(".tasks.bk")).settings.general.tracker_file(wrapper=DKey).to_path()
##--|
@Proto(TaskTracker_i)
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

    def update_state(self, task:str|TaskBase_i|TaskArtifact|TaskName, state:str) -> None:
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

    def _invalidate_descendents(self, task) -> None:
        incomplete, descendants = self._task_dependents(task)
        pass
