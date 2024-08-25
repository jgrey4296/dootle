#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import doot.errors
import more_itertools as mitz
import sh
from doot._abstract import Action_p
from doot.enums import ActionResponse_e as ActRE
from doot.structs import DKey

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

try:
    godot = sh.Command("godot4")
except sh.CommandNotFound as err:
    raise doot.errors.TaskLoadError("godot not found") from err

##-- expansion keys
SCENE      : Final[DKey] = DKey("scene",      implicit=True)
UPDATE     : Final[DKey] = DKey("update",     implicit=True)
SCRIPT     : Final[DKey] = DKey("script",     implicit=True)
QUIT_AFTER : Final[DKey] = DKey("quit_after", implicit=True)
PATH       : Final[DKey] = DKey("path",       implicit=True)
TARGET     : Final[DKey] = DKey("target",     implicit=True)

##-- end expansion keys


@doot.check_protocol
class GodotProjectCheck(Action_p):
    """
      complain if a project.godot file can't be found
    """

    def __call__(self, spec, state):
        if not doot.locs['project.godot'].exists():
            return ActRE.FAIL

@doot.check_protocol
class GodotTestAction(Action_p):

    def __call__(self, spec, task_state):
        try:
            godot_b = godot.bake("--path", doot.locs.root, "--headless")

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Failed to connect") from err

@doot.check_protocol
class GodotRunSceneAction(Action_p):

    def __call__(self, spec, task_state):
        try:
            godot_b    = godot.bake("--path", doot.locs.root, _return_cmd=True)
            scene_file = SCENE.expand(spec, task_state)
            quit_after = QUIT_AFTER.expand(spec, task_state, check=int|str|None)
            if quit_after:
                result = godot_b("--quit-after", quit_after, str(scene_file))
            else:
                result = godot_b(str(scene_file))
            printer.info("Godot Result: %s", result.stdout.decode())
            return { "godot_result" : result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

@doot.check_protocol
class GodotRunScriptAction(Action_p):


    def __call__(self, spec, task_state):
        try:
            godot_b     = godot.bake("--path", doot.locs.root, _return_cmd=True)
            date_key    = UPDATE.redirect(spec)
            script_file = SCRIPT.expand(spec, task_state)
            quit_after  = QUIT_AFTER.expand(spec, task_state, check=int|str|None)
            if quit_after:
                result = godot_b("--quit-after", quit_after, "--headless", "--script", str(script_file))
            else:
                result = godot_b(str(script_file))
            printer.info("Godot Result: %s", result.stdout.decode())
            return { data_key: result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

@doot.check_protocol
class GodotBuildAction(Action_p):


    def __call__(self, spec, task_state):
        try:
            match spec.kwargs.type:
                case "release":
                    godot_b = godot.bake("--path", doot.locs.root, "--export-release", _return_cmd=True)
                case "debug":
                    godot_b = godot.bake("--path", doot.locs.root, "--export-debug", _return_cmd=True)
                case _:
                    raise doot.errors.DootActionError("Bad export type specified, should be `release` or `debug`")

            path_loc = PATH.expand(spec, task_state)
            data_key = UPDATE.expand(spec, task_state)
            result      = godot_b(spec.kwargs.preset, str(path_loc))
            printer.info("Godot Result: %s", result.stdout.decode())
            return { data_key: result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

@doot.check_protocol
class GodotNewSceneAction(Action_p):
    """
      Generate a template new template scene
      to write with write!
    """
    outState = ["sceneText"]

    def __call__(self, spec, task_state):
        # Load the template
        # expand the template with the name
        text = None

        return { "sceneText" : text }

@doot.check_protocol
class GodotNewScriptAction(Action_p):
    """
      Generate a template new gdscript
      to write with write!
    """
    outState = ["scriptText"]

    def __call__(self, spec, task_state):
        # Load the template
        # expand the template with the name
        text = None

        return { "scriptText" : text }

@doot.check_protocol
class GodotCheckScriptsAction(Action_p):


    def __call__(self, spec, task_state):
        try:
            godot_b     = godot.bake("--path", doot.locs.root, "--headless", _return_cmd=True)
            data_key    = UPDATE.expand(spec, task_state)
            script_file = TARGET.expand(spec, task_state)
            result      = godot_b("--check-only", "--script", str(script_file))
            printer.info("Godot Result: %s", result.stdout.decode())
            return { data_key : result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err
