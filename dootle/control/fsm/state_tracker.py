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
from doot._structs.relation_spec import RelationSpec
from doot.enums import (ArtifactStatus_e, EdgeType_e, LocationMeta_e,
                        QueueMeta_e, RelationMeta_e, TaskMeta_e, TaskStatus_e)
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec
from doot.task.core.task import DootTask
from jgdv import Proto

# ##-- end 3rd party imports

from . import _interface as API
from doot.control.split_tracker.track_registry import TrackRegistry
from doot.control.split_tracker.track_network import TrackNetwork
from doot.control.split_tracker.track_queue import TrackQueue

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
   from jgdv import Maybe
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable
   type Abstract[T] = T
   type Concrete[T] = T

##--|
from doot._abstract import Task_p, TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
track_l    = doot.subprinter("track")
fail_l     = doot.subprinter("fail")
skip_l     = doot.subprinter("skip")
task_l     = doot.subprinter("task")
artifact_l = doot.subprinter("artifact")
##-- end logging

@Proto(TaskTracker_p)
class StateTracker:
    """ The public part of the standard tracker implementation
    Has three components:
    _registry : db for specs and tasks
    _network  : the links between specs in the registry
    _queue    : the logic for determining what task to run next

    """

    def __init__(self):
        self._registry = TrackRegistry()
        self._network  = TrackNetwork(self._registry)
        self._queue    = TrackQueue(self._registry, self._network)

    @property
    def active_set(self) -> set:
        return self._queue.active_set

    @property
    def network(self) -> DiGraph:
        return self._network._graph

    @property
    def _root_node(self) -> TaskName:
        return self._network._root_node

    def __bool__(self) -> bool:
        return bool(self._queue)

    def register_spec(self, *specs:TaskSpec)-> None:
        self._registry.register_spec(*specs)

    def queue_entry(self, name:str|Concrete[TaskName|TaskSpec]|TaskArtifact|Task_p, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, parent:Maybe[TaskName]=None) -> Maybe[Concrete[TaskName|TaskArtifact]]:
        queued : TaskName = self._queue.queue_entry(name, from_user=from_user, status=status)
        if not parent:
            return queued
        if '__on_queue' not in self._registry.specs[queued].extra:
            return queued

        parent_task = self._registry.tasks[parent]
        task        = self._registry.tasks[queued]
        for x,y in task.state['__on_queue'].items():
            task.state[x] = y(parent_task.state)
        else:
            return queued

    def get_status(self, task:Concrete[TaskName]|TaskArtifact) -> TaskStatus_e:
        return self._registry.get_status(task)

    def set_status(self, task:Concrete[TaskName]|TaskArtifact|Task_p, state:TaskStatus_e) -> bool:
        self._registry.set_status(task, state)

    def build_network(self, *, sources:Maybe[True|list[Concrete[TaskName]|TaskArtifact]]=None) -> None:
        self._network.build_network(sources=sources)

    def validate_network(self) -> None:
        self._network.validate_network()

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
            self.queue_entry(target, silent=True)

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

    def clear_queue(self):
        self._queue.clear_queue()

    def generate_plan(self):
        pass
