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
import doot.utils.expansion as exp
from doot._abstract import Action_p

try:
    adb = sh.Command("adb")
except sh.CommandNotFound as err:
    raise doot.errors.TaskLoadError("adb not found") from err

TRANSPORT_RE = re.compile("transport_id:([0-9])")

@doot.check_protocol
class AndroidRunning(Action_p):
    """
      Start the adb server and connect to the device.
      internally identifies the transport id and adds it to the task state
    """
    _toml_kwargs = ["update_"]

    def __call__(self, spec, state):
        data_key = exp.to_str(spec.kwargs.on_fail("transport").update_(), spec, state, indirect=True)
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
                raise doot.errors.DootTaskFailed("No Transport Ids Identified")

            return { data_key : transport }
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Failed to connect") from err

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


@doot.check_protocol
class AndroidPush(Action_p):
    _toml_kwargs = ["local", "remote", "from_"]
    inState      = ["android_root"]

    def __call__(self, spec, state):
        try:
            from_key  = exp.to_str(spec.kwargs.on_fail("transport").from_(), spec, state, indirect=True)
            push      = adb.bake("-t", state[from_key], "push", "--sync", _return_cmd=True)
            local     = exp.to_path(spec.kwargs.on_fail("local").local_(), spec, state, indirect=True)
            remote    = exp.to_str(spec.kwargs.on_fail("remote").remote_(), spec, state, indirect=True)
            printer.info("ADB Push: %s -> %s", local, remote)
            result = push(str(local), str(remote))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Push Failed") from err


@doot.check_protocol
class AndroidPull(Action_p):
    _toml_kwargs = ["local", "remote", "from_"]
    inState      = ["android_root"]

    def __call__(self, spec, state):
        result = None
        from_key  = exp.to_str(spec.kwargs.on_fail("transport").from_(), spec, state, indirect=True)
        try:
            pull   = adb.bake("-t", state[from_key], "pull", "-a", _return_cmd=True)
            local  = exp.to_path(spec.kwargs.on_fail("local").local_(), spec, state, indirect=True)
            remote = exp.to_path(spec.kwargs.on_fail("remote").remote_(), spec, state, indirect=True)
            printer.info("ADB Pull: %s -> %s", remote, local)
            # TODO get list of local files, list of remote files, diff, pull those lacking.

            result = pull(str(remote), str(local))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Pull Failed") from err


@doot.check_protocol
class AndroidInstall(Action_p):
    _toml_kwargs = ["package", "from_"]

    def __call__(self, spec, state):
        try:
            from_key = exp.to_str(spec.kwargs.on_fail("transport").from_(), spec, state, indirect=True)
            target   = exp.to_path(spec.kwargs.on_fail("package").package_(), spec, state, indirect=True)
            install  = adb.bake("-t", state[from_key], "install", _return_cmd=True)
            printer.info("ADB Installing: %s", target)
            result = install(str(target))
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s", err.stdout.decode())
            raise doot.errors.DootTaskFailed("Install Failed") from err




@doot.check_protocol
class AndroidRemoteCmd(Action_p):
    inState      = ["transport", "android_root"]
    _toml_kwargs = ["cmd", "update_", "from_"]

    def __call__(self, spec, state):
        try:
            from_key = exp.to_str(spec.kwargs.on_fail("transport").from_(), spec, state, indirect=True)
            data_key = exp.to_str(spec.kwargs.on_fail("adb_result").update_(), spec, state)
            cmd    = adb.bake("-t", state[from_key], "shell", "", _return_cmd=True)
            args   = [exp.to_str(x, spec, state) for x in spec.args]
            printer.info("ADB Cmd: %s : %s", spec.kwargs.cmd, args)
            result = cmd(spec.kwargs.cmd, *args)
            return { data_key : result.stdout.decode() }
        except sh.ErrorReturnCode as err:
            printer.error("ADB Failure: %s : %s", err.stdout.decode(), err.stderr.decode())
            raise doot.errors.DootTaskFailed("Cmd Failed") from err


"""


"""
