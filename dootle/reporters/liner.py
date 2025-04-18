#!/usr/bin/env python3
"""

"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from jgdv import Proto, Mixin
from doot.reporters import _interface as API  # noqa: N812

from . import _interface as LAPI

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    type Logger = logmod.Logger
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

@Proto(API.WorkflowReporter_p, API.GeneralReporter_p)
class LineReporter(API.Reporter_d):
    """ An alternative reporter  """

    def __init__(self, *args, logger:Maybe[Logger]=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logger                 = logger or logging
        self._segments               = LAPI.TRACE_LINES.copy()
        self._log_level              = logmod.INFO
        self._fmt                    = TraceFormatter()
        self.level                   = 0
        self.ctx         : list      = []
        self._act_trace  : list      = []

    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        pass

    def __enter__(self) -> Self:
        self.level += 1
        return self

    def __exit__(self, *exc:Any) -> bool:
        self.level -= 1
        match exc:
            case (None, None, None):
                return True
            case _:
                return False

    def root(self) -> None:
        self._out("root")

    def wait(self) -> None:
        self._out("wait")

    def act(self, info:str, msg:str) -> None:
        self._out("act", info=info, msg=msg)

    def fail(self, info:str, msg:str) -> None:
        self._out("fail")

    def branch(self, name:str) -> Self:
        self._out("branch")
        self.ctx += [self._segments['inactive'], self._segments['gap']]
        self._out("begin", info=name, msg="")
        return self

    def pause (self, reason:str) -> Self:
        self.ctx.pop()
        self.ctx.pop()
        self._out("pause", msg=reason)
        return self

    def result(self, state:list[str]) -> Self:
        self.ctx.pop()
        self.ctx.pop()
        self._out("result", msg=state)
        return self

    def resume(self, name:str) -> Self:
        self._out("resume", msg=name)
        self.ctx += [self._segments['inactive'], self._segments['gap']]
        return self

    def finished(self) -> None:
        self._out("finished")

    def summary(self) -> None:
        pass

    def queue(self, num:int) -> None:
        pass

    def state_result(self, *vals:str) -> None:
        pass

    def _build_ctx(self) -> str:
        return "".join(self.ctx)

    def _out(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> None:
        result = self._fmt(key, info=info, msg=msg, ctx=self.ctx)
        self._logger.log(self._log_level, result)

@Proto(API.TraceFormatter_p)
class TraceFormatter:
    """ An alternative formatter, using some pretty unicode symbols instead of basic ascii """

    def __init__(self):
        self._segments         = LAPI.TRACE_LINES.copy()
        self.line_fmt          = API.LINE_PASS_FMT
        self.msg_fmt           = API.LINE_MSG_FMT

    def _build_ctx(self, ctx:Maybe[list]) -> str:
        match ctx:
            case None:
                return ""
            case list():
                return "".join(ctx)
            case x:
                raise TypeError(type(x))

    def __call__(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, ctx:Maybe[list]=None) -> str:
        extra        = {}
        extra['time']= datetime.datetime.now().strftime("%H:%M")  # noqa: DTZ005
        match self._segments.get(key, None):
            case str() if key in self._segments:
                extra['act'] = self._segments[key]
                extra['gap'] = " "*max(1, (API.ACT_SPACING - len(extra['act'])))
            case (str() as l, str() as m, str() as r):
                # Ensure the same gap between the end of the act, and start of the info
                extra['act'] = f"{l}{m}{r}"
                extra['gap'] = " "*max(1, (API.ACT_SPACING - len(r)))
            case x:
                raise TypeError(type(x))

        match msg:
            case None:
                fmt = self.line_fmt
            case str():
                fmt           = self.msg_fmt
                extra['info'] = info or ""
                # Ensure the same gap between the end of the info, and start of the msg
                extra['gap2'] = " "*max(1, (API.MSG_SPACING - len(extra['info'])))
                extra['detail']  = msg
            case x:
                raise TypeError(type(x))

        extra['ctx'] = self._build_ctx(ctx)
        result : str = fmt.format_map(extra)
        return result
