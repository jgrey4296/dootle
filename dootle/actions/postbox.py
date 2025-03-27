## base_action.py -*- mode: python -*-
"""
  Postbox: Each Task Tree gets one, as a set[Any]
  Each Task can put something in its own postbox.
  And can read any other task tree's postbox, but not modify it.

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
from collections import defaultdict
from time import sleep
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKey, DKeyed
import doot
import sh
from doot._abstract import Action_p
from doot.errors import TaskError, TaskFailed
from doot.structs import TaskName

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)

##-- end logging

STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

##-- expansion keys
UPDATE      : Final[DKey] = DKey("update_")
TASK_NAME   : Final[DKey] = DKey(STATE_TASK_NAME_K)
SUBKEY      : Final[DKey] = DKey("subkey")
##-- end expansion keys

class _DootPostBox:
    """
      Internal Postbox class.
      holds a static variable of `boxes`, which maps task roots -> unique postbox
      Postboxes are lists, values are appended to it

      Can 'put', 'get', 'clear_box', and 'clear'.

      Keys are task names, of {body}..{tail}
      eg: example::task..key
      which corresponds to body[example::task][key]
    """

    boxes : ClassVar[dict[str,list[Any]]] = defaultdict(lambda: defaultdict(list))

    default_subkey                        = "-"
    whole_box_key                         = "*"

    @staticmethod
    def put(key:TaskName, val:None|list|set|Any):
        if key.bmark_e.mark not in key:
            raise ValueError("Tried to use a postbox key with no subkey", key)
        subbox = str(key[-1])
        box    = str(key.root())
        match val:
            case None | [] | {} | dict() if not bool(val):
                pass
            case list() | set():
                _DootPostBox.boxes[box][subbox] += val
            case _:
                _DootPostBox.boxes[box][subbox].append(val)

    @staticmethod
    def get(key:TaskName) -> list|dict:
        if key.bmark_e.mark not in key:
            raise ValueError("tried to get from postbox with no subkey", key)
        box    = str(key.root())
        subbox = str(key[-1])
        match subbox:
            case "*" | None:
                return _DootPostBox.boxes[box].copy()
            case _:
                return _DootPostBox.boxes[box][subbox][:]

    @staticmethod
    def clear_box(key:TaskName):
        if key.bmark_e.mark not in key:
            raise ValueError("tried to clear a box without a subkey", key)
        box    = str(key.root())
        subbox = str(key[-1])
        match subbox:
            case x if x == _DootPostBox.whole_box_key:
                _DootPostBox.boxes[box] = defaultdict(list)
            case _:
                _DootPostBox.boxes[box][subbox] = []

    @staticmethod
    def clear():
        _DootPostBox.boxes.clear()

@Proto(Action_p)
class PutPostAction:
    """
    push data to the inter-task postbox of this task tree
    'args' are pushed to the postbox of the calling task root (ie: stripped of UUIDs)
    'kwargs' are pushed to the kwarg specific subbox. can be explicit tasks or a subbox of the calling task root

    Both key and value are expanded of kwargs.
    The Subbox is the last ..{name} of the full path

    eg: {do="post.put", args=["{key}", "{key}"], "group::task.sub..subbox"="{key}", "subbox"="{key2}"}
    """

    @DKeyed.args
    @DKeyed.kwargs
    @DKeyed.taskname
    def __call__(self, spec, state, args, kwargs, _basename) -> dict|bool|None:
        logging.debug("PostBox Put: %s : args(%s) : kwargs(%s)", _basename, args, list(kwargs.keys()))
        self._add_to_task_box(spec, state, args, _basename)
        self._add_to_target_box(spec, state, kwargs, _basename)

    def _add_to_task_box(self, spec, state, args, _basename):
        target = _basename.root().push(_DootPostBox.default_subkey)
        logging.debug("Adding to task box: %s : %s", target, args)
        for statekey in args:
            data = DKey(statekey, implicit=True).expand(spec, state)
            _DootPostBox.put(target, data)

    def _add_to_target_box(self, spec, state, kwargs, _basename):
        logging.debug("Adding to target boxes: %s", kwargs)
        for box_str, statekey in kwargs.items():
            box_key = DKey(box_str)
            box_key_ex = box_key.expand(spec, state)
            try:
                # Explicit target
                box = TaskName(box_key_ex)
            except ValueError:
                # Implicit
                box = _basename.root().push(box_key_ex)

            match statekey:
                case str():
                    statekey = [statekey]
                case list():
                    pass

            for x in statekey:
                data = DKey(x).expand(spec, state)
                _DootPostBox.put(box, data)

@Proto(Action_p)
class GetPostAction:
    """
      Read data from the inter-task postbox of a task tree.
      'args' pop a value from the calling tasks root (ie: no UUIDs) box into that key name
      'kwargs' are read literally

      stateKey="group::task.sub..{subbox}"
      eg: {do='post.get', args=["first", "second", "third"], data="bib::format..-"}
    """

    @DKeyed.args
    @DKeyed.kwargs
    def __call__(self, spec, state, args, kwargs) -> dict|bool|None:
        result = {}
        result.update(self._get_from_target_boxes(spec, state, kwargs))

        return result

    def _get_from_task_box(self, spec, state, args) -> dict:
        raise NotImplementedError()

    def _get_from_target_boxes(self, spec, state, kwargs) -> dict[DKey,list]:
        updates = {}
        for key,box_str in kwargs.items():
            # Not implicit, as they are the actual lhs to use as the key
            state_key          = DKey(key).expand(spec, state)
            box_key            = DKey(box_str).expand(spec, state)
            target_box         = TaskName(box_key)
            updates[state_key] = _DootPostBox.get(target_box)

        return updates

@Proto(Action_p)
class ClearPostAction:
    """
      Clear your postbox
    """

    @DKeyed.formats("key", fallback=Any)
    @DKeyed.taskname
    def __call__(self, spec, state, key, _basename):
        from_task = _basename.root.push(key)
        _DootPostBox.clear_box(from_task)

@Proto(Action_p)
class SummarizePostAction:
    """
      print a summary of this task tree's postbox
      The arguments of the action are held in self.spec
    """

    @DKeyed.types("from", check=str|None)
    @DKeyed.types("full", check=bool, fallback=False)
    def __call__(self, spec, state, _from, full) -> dict|bool|None:
        from_task = _from or TASK_NAME.expand(spec, state).root
        data   = _DootPostBox.get(from_task)
        if full:
            for x in data:
                doot.report.trace("Postbox %s: Item: %s", from_task, str(x))

        doot.report.trace("Postbox %s: Size: %s", from_task, len(data))
