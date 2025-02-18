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
import doot
import doot.errors
import sh
from doot._abstract import Action_p
from doot.structs import DKey, DKeyed

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
printer = doot.subprinter()
##-- end logging

try:
    adb = sh.Command("adb")
except sh.CommandNotFound as err:
    raise doot.errors.TaskLoadError("adb not found") from err

TRANSPORT_RE = re.compile("transport_id:([0-9])")
##--|
@Proto(Action_p)
class AndroidRunning:
    """
      Start the adb server and connect to the device.
      internally identifies the transport id and adds it to the task state
    """

    @DKeyed.redirects("transport")
    @DKeyed.returns("transport")
    def __call__(self, spec, state, transport):
        data_key = transport
        try:
            adb("start-server", _bg=True)
            transport = self._get_transport_id()
            if transport:
                printer.info("ADB connected, transport id: %s", transport)
                return { data_key : transport }

            device = input("Device Ip:Port: ")
            result = adb("connect", device, _return_cmd=True)
            printer.info("ADB: %s", result.stdout.decode())
            transport = self._get_transport_id()
            if not transport:
                raise doot.errors.TaskFailed("No Transport Ids Identified")

            return { data_key : transport }
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.TaskFailed("Failed to connect") from err

    def _get_transport_id(self) -> None|str:
        result = adb("devices", "-l", _return_cmd=True)
        result_str = result.stdout.decode()
        match TRANSPORT_RE.findall(result_str):
            case [x]:
                return x
            case [] | None:
                return None
            case [*xs]:
                printer.info("Multiple Transport Ids Found, select one:")
                printer.info("%s", xs)
                return input("Transport Id: ")

@Proto(Action_p)
class AndroidPush:

    @DKeyed.formats("transport")
    @DKeyed.paths("local", "remote")
    def __call__(self, spec, state, transport, local, remote):
        try:
            push        = adb.bake("-t", transport, "push", "--sync", _return_cmd=True)
            printer.info("ADB Push: %s -> %s", local, remote)
            result = push(str(local), str(remote))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.TaskFailed("Push Failed") from err

@Proto(Action_p)
class AndroidPull:

    @DKeyed.formats("transport")
    @DKeyed.paths("local", "remote")
    def __call__(self, spec, state, transport, local, remote):
        result     = None
        try:
            pull   = adb.bake("-t", transport, "pull", "-a", _return_cmd=True)
            printer.info("ADB Pull: %s -> %s", remote, local)
            # TODO get list of local files, list of remote files, diff, pull those lacking.

            result = pull(str(remote), str(local))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.TaskFailed("Pull Failed") from err

@Proto(Action_p)
class AndroidInstall:

    @DKeyed.formats("transport")
    @DKeyed.paths("package")
    def __call__(self, spec, state, transport, package):
        try:
            target   = package
            install  = adb.bake("-t", transport, "install", _return_cmd=True)
            printer.info("ADB Installing: %s", target)
            result = install(str(target))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.TaskFailed("Install Failed") from err

@Proto(Action_p)
class AndroidRemoteCmd:

    @DKeyed.args
    @DKeyed.formats("transport", "cmd")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, transport, cmd, _update):
        try:
            data_key  = _update
            adb_cmd   = adb.bake("-t", transport, "shell", "", _return_cmd=True)
            args      = [DKey(x, fallback=x, mark=DKey.Mark.MULTI).expand(spec, state) for x in spec.args]
            printer.info("ADB Cmd: %s : %s", cmd, args)
            result = adb_cmd(cmd, *args)
            return { data_key : result.stdout.decode() }
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s : %s", err.stdout.decode(), err.stderr.decode())
            raise doot.errors.TaskFailed("Cmd Failed") from err
