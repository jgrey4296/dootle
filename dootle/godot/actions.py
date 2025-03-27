#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors
import sh
from doot._abstract import Action_p
from doot.enums import ActionResponse_e as ActRE

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

try:
    godot = sh.Command("godot4")
except sh.CommandNotFound as err:
    raise doot.errors.TaskLoadError("godot not found") from err


@Proto(Action_p)
class GodotProjectCheck:
    """
      complain if a project.godot file can't be found
    """

    def __call__(self, spec, state):
        if not doot.locs['{project.godot}'].exists():
            return ActRE.FAIL

@Proto(Action_p)
class GodotTestAction:

    def __call__(self, spec, state):
        try:
            godot_b = godot.bake("--path", doot.locs.root, "--headless")

        except sh.ErrorReturnCode as err:
            doot.report.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Failed to connect") from err

@Proto(Action_p)
class GodotRunSceneAction:

    @DKeyed.paths("scene")
    @DKeyed.types("quit_after", check=int|str|None, fallback=None)
    def __call__(self, spec, state, scene, _qa):
        try:
            godot_b    = godot.bake("--path", doot.locs.root, _return_cmd=True)
            match _qa:
                case int()|str():
                    result = godot_b("--quit-after", _qa, str(scene))
                case _:
                    result = godot_b(str(scene))

            doot.report.trace("Godot Result: %s", result.stdout.decode())
            return { "godot_result" : result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            doot.report.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

@Proto(Action_p)
class GodotRunScriptAction:

    @DKeyed.paths("script")
    @DKeyed.types("quit_after", check=int|str|None, fallback=None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, script, _qa, _update):
        try:
            godot_b     = godot.bake("--path", doot.locs.root, _return_cmd=True)
            match _qa:
                case int()|str():
                    result = godot_b("--quit-after", _qa, "--headless", "--script", str(script))
                case _:
                    result = godot_b(str(script))

            doot.report.trace("Godot Result: %s", result.stdout.decode())
            return { _update : result.stdout.decode() }

        except sh.ErrorReturnCode as err:
            doot.report.error("Godot Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Godot Failed") from err

@Proto(Action_p)
class GodotBuildAction:

    @DKeyed.formats("preset")
    @DKeyed.kwargs
    @DKeyed.paths("path")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, preset, kwargs, path, _update):
        match kwargs:
            case {"type": "release"}:
                godot_b = godot.bake("--path", doot.locs.root, "--export-release", _return_cmd=True)
            case {"type" : "debug"}:
                godot_b = godot.bake("--path", doot.locs.root, "--export-debug", _return_cmd=True)
            case _:
                raise doot.errors.ActionError("Bad export type specified, should be `release` or `debug`")

        try:
            result      = godot_b(preset, str(path))
            stdout = result.stdout.decode()
            doot.report.trace("Godot Result: %s", stdout)
            return { _update: stdout }
        except sh.ErrorReturnCode as err:
            stdout = result.stdout.decode()
            stderr = err.stdout.decode()
            doot.report.error("Godot Failure: %s", stderr)
            raise doot.errors.DootTaskFailed("Godot Failed", stdout, stderr) from err

@Proto(Action_p)
class GodotNewSceneAction:
    """
      Generate a template new template scene
      to write with write!
    """

    def __call__(self, spec, state):
        # Load the template
        # expand the template with the name
        text = None

        # return { "sceneText" : text }
        raise NotImplementedError()

@Proto(Action_p)
class GodotNewScriptAction:
    """
      Generate a template new gdscript
      to write with write!
    """

    def __call__(self, spec, state):
        # Load the template
        # expand the template with the name
        text = None

        # return { "scriptText" : text }
        raise NotImplementedError()

@Proto(Action_p)
class GodotCheckScriptsAction:

    @DKeyed.paths("target")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, target, _update):

        godot_b     = godot.bake("--path", doot.locs.root, "--headless", _return_cmd=True)
        try:
            result      = godot_b("--check-only", "--script", str(target))
            stdout = result.stdout.decode()
            doot.report.trace("Godot Result: %s", stdout)
            return { _update : stdout }
        except sh.ErrorReturnCode as err:
            stdout = result.stdout.decode()
            stderr = result.stderr.decode()
            doot.report.error("Godot Failure: %s", stderr)
            raise doot.errors.DootTaskFailed("Godot Failed", stdout, stderr) from err
