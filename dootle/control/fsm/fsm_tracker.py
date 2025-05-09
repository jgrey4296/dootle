#!/usr/bin/env python3
"""
An Alternative task tracker for doot.
Uses FSM's to simplify StateTracker.next_for.

The FSM wraps a DootTask/Job/Artifact, and manages its progression

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
import weakref
from collections import defaultdict
from itertools import chain, cycle
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import doot.errors
from doot.workflow import RelationSpec, DootTask, ActionSpec
from doot.workflow._interface import (ArtifactStatus_e, QueueMeta_e, RelationMeta_e, TaskMeta_e)
from doot.control.tracker._interface import EdgeType_e
from jgdv import Proto
from jgdv.structs.locator._interface import LocationMeta_e

# ##-- end 3rd party imports

from . import _interface as API  # noqa: N812
from doot.control.tracker import Tracker_abs
from doot.control.tracker._interface import TaskTracker_p
from doot.control.tracker.registry import TrackRegistry
from doot.control.tracker.network import TrackNetwork
from doot.control.tracker.queue import TrackQueue

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
   from doot.workflow._interface import Task_p
   from doot.workflow import TaskArtifact, TaskName, TaskSpec
   from doot.workflow._interface import TaskStatus_e
   from jgdv import Maybe
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

   import networkx as nx
   type Abstract[T] = T
   type Concrete[T] = T

##--|
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

@Proto(TaskTracker_p)
class FSMTracker(Tracker_abs):
    """

    """

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        focus : str|TaskName|TaskArtifact
        count : int
        result : Maybe[Task_p|TaskArtifact]
        status : TaskStatus_e

        logging.info("[Next.For] (Active: %s)", len(self._queue.active_set))
        if not self._network.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue_entry(target)

        count  = API.MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus  = self._queue.deque_entry()
            status = self._registry.get_status(focus)
            logging.debug("[Next.For.Head]: %s : %s", status, focus)

            # Run The FSM of the task/artifact

        else:
            logging.info("[Next.For] <- %s", result)
            # wrap the result in an execution FSM
            return result
