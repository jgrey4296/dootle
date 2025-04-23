## base_action.py -*- mode: python -*-
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
import sys
import time
import types
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

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

EXITCODES : Final[list[int]] = [0]
##--|
@Proto(Action_p)
class SayAction:
    """
    A Simple Action to trigger speech synthesis
    Will say anything expanded from the action specs 'args'

    """
    mac_announce_args : ClassVar[list[str]] = ["-v", "Moira", "-r", "50"]

    @DKeyed.args
    def __call__(self, spec, state, args):
        try:
            match sys.platform:
                case "linux":
                    return self._say_linux(spec, state)
                case "darwin":
                    return self._say_mac(spec, state)
                case _:
                    return False
        except sh.ForkException as err:
            doot.report.error("Shell Command failed: %s", err)
        except sh.CommandNotFound as err:
            doot.report.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
        except sh.ErrorReturnCode as err:
            doot.report.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                doot.report.error("-- Stdout: ")
                doot.report.error("%s", err.stdout.decode())
                doot.report.error("")
                doot.report.error("-- Stdout End")
                doot.report.error("")

            doot.report.gap()
            if bool(err.stderr):
                doot.report.error("-- Stderr: ")
                doot.report.error("%s", err.stderr.decode())
                doot.report.error("")
                doot.report.error("-- Stderr End")
                doot.report.error("")

        return False

    @DKeyed.args
    @DKeyed.types("wait", fallback=5, check=int)
    @DKeyed.types("background", fallback=False, check=bool)
    def _say_linux(self, spec, state, args, wait, background) -> bool:
        cmd    = sh.espeak
        keys                    = [DKey(x, mark=DKey.Mark.MULTI, fallback=x) for x in args[0:]]
        expanded                = [str(x.expand(spec, state)) for x in keys]
        result = cmd(*expanded, _return_cmd=True, _bg=background)
        if result.exit_code not in EXITCODES:
            doot.report.warn("Shell Command Failed: %s", result.exit_code)
            doot.report.warn(result.stderr.decode())
            return False

        logging.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        logging.info("%s", result, extra={"colour":"reset"})
        sleep(wait)
        return True


    @DKeyed.args
    @DKeyed.types("wait", fallback=5, check=int)
    @DKeyed.types("background", fallback=False, check=bool)
    def _say_mac(self, spec, state, args, wait, background) -> bool:
        cmd    = sh.say
        keys                    = [DKey(x, mark=DKey.Mark.MULTI, fallback=x) for x in args[0:]]
        expanded                = [str(x.expand(spec, state)) for x in keys]
        result = cmd(*args, _return_cmd=True, _bg=background)
        if result.exit_code not in EXITCODES:
            doot.report.warn("Shell Command Failed: %s", result.exit_code)
            doot.report.warn(result.stderr.decode())
            return False

        logging.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        logging.info("%s", result, extra={"colour":"reset"})
        sleep(wait)
        return True


@Proto(Action_p)
class SayTimeAction:
    """
    A Simple Action that announces the time
    Subclass this and override __call__ for your own actions.
    The arguments of the action are held in self.spec

    """
    _toml_kwargs = ["wait", "background"]
    mac_announce_args = ["-v", "Moira", "-r", "50", "The Time Is "]
    linux_announce_args = ["The Time Is "]
    time_format   = "%H:%M"

    def _current_time(self) -> str:
        now = datetime.datetime.now()
        return now.strftime(self.time_format)

    @DKeyed.args
    def __call__(self, spec, state, args):
        try:
            match sys.platform:
                case "linux":
                    return self._say_linux(spec, state)
                case "darwin":
                    return self._say_mac(spec, state)
                case _:
                    return False
        except sh.CommandNotFound as err:
            doot.report.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
            return False
        except sh.ErrorReturnCode:
            doot.report.error("Shell Command '%s' exited with code: %s for args: %s", args[0], result.exit_code, args)
            return False


    def _say_linux(self, spec, state:dict):
        cmd    = sh.espeak
        args   = (spec.args or self.mac_announce_args) + [self._current_time()]
        if spec.kwargs.on_fail(False, bool).wait():
            sleep(10)
        result = cmd(*args, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
        assert(result.exit_code == 0)
        doot.report.detail("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        doot.report.trace("%s", result, extra={"colour":"reset"})
        return True


    def _say_mac(self, spec, state:dict):
        cmd    = sh.say
        args   = (spec.args or self.mac_announce_args) + [self._current_time()]
        if spec.kwargs.on_fail(False, bool).wait():
            sleep(10)
        result = cmd(*args, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
        assert(result.exit_code == 0)
        doot.report.detail("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        doot.report.trace("%s", result, extra={"colour":"reset"})
        return True
