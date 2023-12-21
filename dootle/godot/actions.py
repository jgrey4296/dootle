#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer = logmod.getLogger("doot._printer")

import sh
import doot
import doot.errors
from doot._abstract import Action_p
from doot.enums import ActionResponseEnum as ActRE
import doot.utils.expansion as exp

try:
    godot = sh.Command("godot4")
except sh.CommandNotFound as err:
    raise doot.errors.TaskLoadError("godot not found") from err

##-- expansion keys
SCENE      : Final[exp.DootKey] = exp.DootKey("scene")
UPDATE     : Final[exp.DootKey] = exp.DootKey("update")
SCRIPT     : Final[exp.DootKey] = exp.DootKey("script")
QUIT_AFTER : Final[exp.DootKey] = exp.DootKey("quit_after")
PATH       : Final[exp.DootKey] = exp.DootKey("path")
TARGET     : Final[exp.DootKey] = exp.DootKey("target")

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

    _toml_kwargs = [QUIT_AFTER, SCENE]

    def __call__(self, spec, task_state):
        try:
            godot_b    = godot.bake("--path", doot.locs.root, _return_cmd=True)
            scene_file = SCENE.to_path(spec, task_state)
            quit_after = QUIT_AFTER.to_type(spec, task_state, type_=int|str|None)
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

    _toml_kwargs = [UPDATE, QUIT_AFTER, SCRIPT]

    def __call__(self, spec, task_state):
        try:
            godot_b     = godot.bake("--path", doot.locs.root, _return_cmd=True)
            date_key    = UPDATE.redirect(spec)
            script_file = SCRIPT.to_path(spec, task_state)
            quit_after  = QUIT_AFTER.to_type(spec, task_state, type_=int|str|None)
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

    _toml_kwargs = [PATH, UPDATE, "preset"]

    def __call__(self, spec, task_state):
        try:
            match spec.kwargs.type:
                case "release":
                    godot_b = godot.bake("--path", doot.locs.root, "--export-release", _return_cmd=True)
                case "debug":
                    godot_b = godot.bake("--path", doot.locs.root, "--export-debug", _return_cmd=True)
                case _:
                    raise doot.errors.DootActionError("Bad export type specified, should be `release` or `debug`")

            path_loc = PATH.to_path(spec, task_state)
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
    _toml_kwargs = ["name", "template"]
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
    _toml_kwargs = ["name", "template"]
    outState = ["scriptText"]

    def __call__(self, spec, task_state):
        # Load the template
        # expand the template with the name
        text = None

        return { "scriptText" : text }

@doot.check_protocol
class GodotCheckScriptsAction(Action_p):

    _toml_kwargs = [UPDATE, TARGET]

    def __call__(self, spec, task_state):
        try:
            godot_b     = godot.bake("--path", doot.locs.root, "--headless", _return_cmd=True)
            data_key    = UPDATE.expand(spec, task_state)
            script_file = TARGET.to_path(spec, task_state)
            result      = godot_b("--check-only", "--script", str(script_file))
            printer.info("Godot Result: %s", result.stdout.decode())
            return { data_key : result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            printer.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

"""

"""
