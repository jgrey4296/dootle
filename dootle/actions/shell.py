"""

"""
# ruff: noqa: ANN001, PLR0913
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import sys
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto
import doot
import sh
from doot._abstract import Action_p
from doot.actions.base_action import DootBaseAction
from doot.errors import TaskError
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
fail_l  = doot.subprinter("fail")
##-- end logging
@Proto(Action_p)
class DootShellBake:
    """
      Create a pre-baked shell command for reuse as in a ShellBakedRun,
      for chaining commands without returning to doot
      args are explicit

    eg: {do='bake!', args=[...], update_="baked"},
    ... {do="bake!', args=[...], in_="baked", update_="baked"},
    ... {do="run!",  in_="baked", update_="result"}
    """

    @DKeyed.args
    @DKeyed.redirects("in_")
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, args, _in, env, _update):
        env      = env or sh
        keys     = [DKey(x) for x in args]
        expanded = [x.expand(spec, state) for x in keys]
        try:
            cmd                     = getattr(env, expanded[0])

            match _in.expand(spec, state, fallback=None, check=sh.Command|bool|None):
                case False | None:
                    baked = cmd.bake(*expanded[1:], _return_cmd=True, _tty_out=False)
                case sh.Command() as x:
                    baked = cmd.bake(*expanded[1:], _in=x(), _return_cmd=True, _tty_out=False)
                case _:
                    raise TaskError("Bad pre-command for shell baking", _in)
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
            return False
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

            return False
        else:
            return { _update : baked }

        return False

@Proto(Action_p)
class DootShellBakedRun:
    """
      Run a series of baked commands
    """

    @DKeyed.redirects("in_")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, _in, _update):
        cmd    = _in.expand(spec,state, check=sh.Command|None)
        try:
            result = cmd()
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0])
            return False
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

            return False
        else:
            return { _update : result }

@Proto(Action_p)
class DootShellAction:
    """
    For actions in subshells/processes.
    all other arguments are passed directly to the program, using `sh`

    can use a pre-baked sh passed into what "shenv_" points to
    """

    @DKeyed.args
    @DKeyed.types("background", "notty", check=bool, fallback=False)
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    @DKeyed.paths("cwd", fallback=".", check=pl.Path|None)
    @DKeyed.types("exitcodes", fallback=[0])
    @DKeyed.toggles("splitlines", fallback=False)
    @DKeyed.redirects("update_", fallback=None)
    def __call__(self, spec, state, args, background, notty, env, cwd, exitcodes, splitlines, _update) -> dict|bool|None:
        result     = None
        env        = env or sh
        keys                    = [DKey(x, mark=DKey.Mark.MULTI, fallback=x) for x in args]
        expanded                = [str(x.expand(spec, state)) for x in keys]
        try:
            # Build the command by getting it from env:
            cmd_name                = expanded[0]
            cmd                     = getattr(env, cmd_name)
            result                  = cmd(*expanded[1:],
                                          _return_cmd=True,
                                          _bg=background,
                                          _tty_out=not notty,
                                          _cwd=cwd,
                                          _iter=True)

        except sh.ForkException as err:
            fail_l.error("Shell Command failed: %s", err)
            return False
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
            return False
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("-- Stderr: ")
                fail_l.error("%s", err.stderr.decode())
                fail_l.error("")
                fail_l.error("-- Stderr End")
                fail_l.error("")

            return False
        else:
            for line in result:
                printer.user("(Cmd): %s", line.strip())

            for errline in result.stderr.decode().splitlines():
                printer.user("(CmdErr): %s", errline)
            if result.exit_code not in exitcodes:
                printer.user("Shell Command Failed: %s", result.exit_code)
                return False

            printer.debug("Shell Cwd: %s", cwd)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd_name, args[1:])

            match _update:
                case None:
                    return True
                case str() if splitlines:
                    return { _update : result.stdout.decode().splitlines()}
                case str():
                    return { _update : result.stdout.decode() }
                case x:
                    raise TypeError("Unexpected 'update' type", x)

@Proto(Action_p)
class DootInteractiveAction:
    """
      An interactive command, which uses the self.interact method as a callback for sh.

    see: https://sh.readthedocs.io/en/latest/sections/asynchronous_execution.html#interactive-callbacks
    """
    aggregated = ""
    prompt     = ">>> "
    cont       = "... "

    @DKeyed.formats("prompt", "cont")
    @DKeyed.args
    @DKeyed.types("env", fallback=None, check=sh.Command|None)
    def __call__(self, spec, state:dict, prompt, cont, args, env) -> dict|bool|None:
        try:
            self.prompt             = prompt or self.prompt
            self.cont               = cont or self.cont
            env                     = env or sh
            cmd                     = getattr(env, DKey(args[0], fallback=args[0]).expand(spec, state))
            args                    = spec.args[1:]
            keys                    = [DKey(x, mark=DKey.Mark.MULTI, fallback=x) for x in args[1:]]
            expanded                = [str(x.expand(spec, state)) for x in keys]
            result                  = cmd(*expanded, _return_cmd=True, _bg=False, _out=self.interact, _out_bufsize=0, _tty_in=True, _unify_ttys=True)
            assert(result.exit_code == 0)
            printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, spec.args[0], spec.args[1:])
            printer.info("%s", result, extra={"colour":"reset"})

        except sh.ForkException as err:
            fail_l.error("Shell Command failed: %s", err)
            return False
        except sh.CommandNotFound as err:
            fail_l.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
            return False
        except sh.ErrorReturnCode as err:
            fail_l.error("Shell Command '%s' exited with code: %s", err.full_cmd, err.exit_code)
            if bool(err.stdout):
                fail_l.error("%s", err.stdout.decode())

            fail_l.info("")
            if bool(err.stderr):
                fail_l.error("%s", err.stderr.decode())

            return False
        else:
            return True

    def interact(self, char, stdin) -> None:
        # TODO possibly add a custom interupt handler/logger
        self.aggregated += str(char)
        if self.aggregated.endswith("\n"):
            printer.info(self.aggregated.strip())
            self.aggregated = ""

        if self.aggregated.startswith(self.prompt) :
            prompt = self.aggregated[:] + ": "
            self.aggregated = ""
            stdin.put(input(prompt) + "\n")
        elif self.aggregated.startswith(self.cont):
            self.aggregated = ""
            val = input(self.cont)
            if bool(val):
                stdin.put("    " + input(self.cont) + "\n")
            else:
                stdin.put(input(self.cont) + "\n")
