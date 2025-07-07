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
import sh
from jgdv import Proto, Maybe
from jgdv.structs.strang import StrangError
import doot
from doot.util.dkey import DKey, DKeyed
from doot.workflow._interface import Action_p
from doot.workflow import TaskName
from doot.errors import TaskError, TaskFailed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)

##-- end logging

STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

NO_SUBBOX : Final[str] = "The Provided key doesn't have a subbox"
##-- expansion keys
TASK_NAME   : Final[DKey] = DKey[TaskName](STATE_TASK_NAME_K, implicit=True)
##-- end expansion keys
def _validate_key(key:TaskName) -> tuple[str,str]:
    """ Validate and split a key into (box, subbox) """
    match key.args():
        case [x]:
            subbox = x
        case ["<uuid>", x]:
            subbox = x
        case ["<uuid>"]:
            subbox = key.uuid()
        case _:
            subbox = _DootPostBox.default_subbox
    ##--|
    assert(subbox is not None)
    return key[:,:], subbox

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

    boxes : ClassVar[dict[str,dict[str, list[Any]]]]  = defaultdict(lambda: defaultdict(list))

    default_subbox                                    = "-"
    whole_box_key                                     = "*"

    @staticmethod
    def put(key:TaskName, val:None|list|set|Any) -> None:
        box, subbox = _validate_key(key)
        match val:
            case None | [] | {} | dict() if not bool(val):
                pass
            case list() | set():
                _DootPostBox.boxes[box][subbox] += val
            case _:
                _DootPostBox.boxes[box][subbox].append(val)

    @staticmethod
    def get(key:TaskName) -> list|dict:
        box, subbox = _validate_key(key)
        match subbox:
            case "*" | None:
                return _DootPostBox.boxes[box].copy()
            case _:
                return _DootPostBox.boxes[box][subbox][:]

    @staticmethod
    def clear_box(key:TaskName) -> None:
        box, subbox = _validate_key(key)
        match subbox:
            case x if x == _DootPostBox.whole_box_key:
                _DootPostBox.boxes[box] = defaultdict(list)
            case _:
                _DootPostBox.boxes[box][subbox] = []

    @staticmethod
    def clear() -> None:
        _DootPostBox.boxes.clear()

##--| Actions:
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
    def __call__(self, spec, state, args, kwargs, _basename) -> None:  # noqa: ANN001
        logging.debug("PostBox Put: %s : args(%s) : kwargs(%s)", _basename, args, list(kwargs.keys()))
        self._add_to_task_box(spec, state, args, _basename)
        self._add_to_target_box(spec, state, kwargs, _basename)

    def _add_to_task_box(self, spec, state, args, _basename) -> None:  # noqa: ANN001
        logging.debug("Adding to task box: %s : %s", _basename, args)
        for statekey in args:
            data = DKey(statekey, implicit=True).expand(spec, state)
            _DootPostBox.put(_basename, data)

    def _add_to_target_box(self, spec, state, kwargs, _basename) -> None:  # noqa: ANN001
        logging.debug("Adding to target boxes: %s", kwargs)
        targets  : list[DKey]
        box_key  : DKey
        box      : TaskName

        for box_str, statekey in kwargs.items():
            box_key = DKey(box_str).expand(spec, state)
            try:
                # Explicit target
                box = TaskName(box_key)
            except StrangError:
                # Implicit
                box = _basename.push(box_key)

            match statekey:
                case DKey():
                    targets = [statekey]
                case str():
                    targets = [DKey(statekey)]
                case [*xs]:
                    targets = [DKey(x) for x in xs]
                case x:
                    raise TypeError(type(x))

            for x in targets:
                data = x.expand(spec, state)
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
    def __call__(self, spec, state, args, kwargs) -> Maybe[dict|bool]:  # noqa: ANN001, ARG002
        result = {}
        result.update(self._get_from_target_boxes(spec, state, kwargs))

        return result

    def _get_from_task_box(self, spec, state, args) -> dict:  # noqa: ANN001
        raise NotImplementedError()

    def _get_from_target_boxes(self, spec, state, kwargs) -> dict[DKey,list|dict]:  # noqa: ANN001
        updates : dict[DKey, list|dict] = {}
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
    def __call__(self, spec, state, key, _basename) -> None:  # noqa: ANN001, ARG002
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
    def __call__(self, spec, state, _from, full) -> Maybe[dict|bool]:  # noqa: ANN001
        from_task  = _from or TASK_NAME.expand(spec, state).root
        data       = _DootPostBox.get(from_task)
        if full:
            for x in data:
                doot.report.gen.trace("Postbox %s: Item: %s", from_task, str(x))

        doot.report.gen.trace("Postbox %s: Size: %s", from_task, len(data))
