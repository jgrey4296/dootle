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
from doot.control.tracker import Tracker_abs
from doot.control.tracker._interface import EdgeType_e, WorkflowTracker_p, Registry_d
from doot.control.tracker.network import TrackNetwork
from doot.control.tracker.queue import TrackQueue
from doot.control.tracker.registry import TrackRegistry
from doot.workflow import (ActionSpec, DootTask, RelationSpec, TaskArtifact,
                           TaskName)
from doot.workflow._interface import (ArtifactStatus_e, QueueMeta_e,
                                      RelationMeta_e, Task_p, TaskMeta_e,
                                      TaskStatus_e, RelationSpec_i, InjectSpec_i, TaskName_p)
from jgdv import Proto
from jgdv.structs.locator._interface import LocationMeta_e

# ##-- end 3rd party imports

from . import _interface as API  # noqa: N812
from .machines import TaskMachine
from .factory import FSMFactory

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
   from doot.workflow._interface import TaskSpec_i, Artifact_i
   from doot.util._interface import DelayedSpec
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

@Proto(WorkflowTracker_p)
class FSMTracker(Tracker_abs):
    """
    Tracks tasks by their FSM state

    TODO modify default ctor's of specs to be FSMTask on register

    """
    machines : dict[TaskName, TaskMachine]

    def __init__(self, **kwargs:Any) -> None:
        kwargs.setdefault("factory", FSMFactory)
        super().__init__(**kwargs)
        self.machines = {}
        # Update the aliases so the default ctor for tasks is an FSMTask
        doot.update_aliases(data=API.ALIASES_UPDATE)

    ##--| main logic

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:
        """ ask for the next task that can be performed

            Returns a Task or Artifact that needs to be executed or created
            Returns None if it loops too many times trying to find a target,
            or if theres nothing left in the queue

        """
        focus   : TaskName|TaskArtifact
        count   : int
        idx     : int
        result  : Maybe[TaskMachine|Task_p|TaskArtifact]
        logging.info("[Next.For] (Active: %s)", len(self._queue.active_set))
        if not self.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue(target)

        idx, count  = 0, API.MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1) and (idx:=idx+1):
            focus  = self._queue.deque_entry()
            logging.debug("[Next.For.%-3s]: %s", idx, focus)
            match focus:
                case TaskName_p() as x if x in self._registry.specs:
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

    @override
    def queue(self, name:str|TaskName_p|TaskSpec_i|Artifact_i, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName_p|Artifact_i]]:
        match super().queue(name, from_user=from_user, status=status):
            case TaskName() as queued if queued not in self.machines:
                logging.debug("[Next.For] Queue run")
                # instantiate FSM task
                self._instantiate(queued, task=True)
                return queued
            case x:
                return x

    @override
    def _instantiate(self, target:TaskName_p|RelationSpec_i, *args:Any, task:bool=False, **kwargs:Any) -> Maybe[TaskName_p]:
        """ when a task is created, create a state machine for it as well """
        parent : TaskName_p
        result : Maybe[TaskName_p]
        ##--|
        parent  = kwargs.pop("parent", None)
        match super()._instantiate(target, *args, task=task, **kwargs):
            case TaskName_p() as result if task and result not in self.machines:
                task_inst              = self._registry.specs[result].task
                fsm                    = TaskMachine(task_inst)
                self.machines[result]  = fsm
                fsm.run_until_init(self)
            case TaskName_p() as result:
                return result
            case None:
                return None
            case x:
                raise TypeError(type(x))

    ##--| utils

    def get_status(self, *, target:Maybe[TaskName_p]=None) -> tuple[TaskStatus_e, int]:
        match self.machines.get(target, None):
            case None if target == self._root_node:
                return TaskStatus_e.NAMED, self._declare_priority
            case None if target in self.specs:
                return TaskStatus_e.DECLARED, self._declare_priority
            case TaskMachine() as x:
                return x.current_state_value, x.model.priority
            case x:
                raise TypeError(type(x))

    def set_status(self, *args:Any) -> None:
        """ No-op as the FSM's control status """
        pass

    def _dependency_states_of(self, focus:TaskName_p) -> list[tuple]:
        return [(x, self.get_status(target=x)[0]) for x in self._network.pred[focus] if x != self._root_node]

    def _successor_states_of(self, focus:TaskName_p) -> list[tuple]:
        return [(x, self.get_status(target=x)[0]) for x in self._network.succ[focus] if x != self._root_node]
