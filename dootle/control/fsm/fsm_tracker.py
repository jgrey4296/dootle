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
from doot.workflow import TaskArtifact, TaskName
from doot.workflow._interface import TaskStatus_e, Task_p
from .machines import TaskMachine

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
   from doot.workflow import TaskSpec
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

##--|

@Proto(TaskTracker_p)
class FSMTracker(Tracker_abs):
    """
    Tracks tasks by their FSM state

    TODO modify default ctor's of specs to be FSMTask on register

    """
    machines : dict[TaskName, TaskMachine]

    def __init__(self):
        super().__init__()
        self.machines = {}
        # Update the aliases so the default ctor for tasks is an FSMTask
        doot.update_aliases(data=API.ALIASES_UPDATE)


    def _get_priority(self, target:Concrete[TaskName|TaskArtifact]) -> int:
        match self.tasks.get(target, None):
            case None:
                return self._declare_priority
            case Task_p() as x:
                return x.priority
            case x:
                raise TypeError(type(x))

    def get_status(self, name:TaskName) -> TaskStatus_e:
        match self.machines.get(name, None):
            case None if name in self.specs:
                return TaskStatus_e.DECLARED
            case TaskMachine() as x:
                return x.current_state_value
            case x:
                raise TypeError(type(x))

    def set_status(self, *args:Any) -> None:
        pass

    def queue(self, name:str|Concrete[TaskName|TaskSpec]|TaskArtifact, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName|TaskArtifact]]:
        match super().queue(name, from_user=from_user, status=status):
            case TaskName() as queued if queued not in self.machines:
                # instantiate FSM task
                self._registry.make_task(queued, parent=kwargs.pop("parent", None))
                task = self._registry.tasks[queued]
                fsm = TaskMachine(task)
                self.machines[queued] = fsm
                fsm.run_until_init(self)
                return queued
            case x:
                return x

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        focus   : TaskName|TaskArtifact
        count   : int
        result  : Maybe[TaskMachine|Task_p|TaskArtifact]
        logging.info("[Next.For] (Active: %s)", len(self._queue.active_set))
        if not self.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue(target)

        count  = API.MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus  = self._queue.deque_entry()
            logging.debug("[Next.For.Head]: %s", focus)
            match focus:
                case TaskName() as x if x in self._registry.tasks:
                    # get and run the machine
                    fsm   = self.machines[x]
                    match fsm.current_state_value:
                        case TaskStatus_e.READY | TaskStatus_e.TEARDOWN | TaskStatus_e.RUNNING:
                            # Ready to be executed, pass to the runner
                            result = fsm.model
                        case TaskStatus_e.DEAD:
                            # is dead, nothing to do
                            pass
                        case TaskStatus_e.WAIT | TaskStatus_e.INIT:
                            # not ready to execute yet
                            fsm.run_until_ready(self)
                            self.queue(x)
                        case x:
                            raise TypeError(type(x), x)
                case TaskArtifact() as x:
                    return x
                case _:
                    continue
        else:
            logging.info("[Next.For] <- %s", result)
            # wrap the result in an execution FSM
            return result
