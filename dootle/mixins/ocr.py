#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot

ocr_out_ext      : Final[str] = doot.config.on_fail(".ocr", str).images.ocr_out()

class OCRMixin:

    def get_ocr_file_name(self, fpath):
        return fpath.parent / f".{fpath.stem}{ocr_out_ext}"

    def make_ocr_cmds(self, fpath, dst=None):
        """
        outputs to cwd dst.txt
        """
        dst = dst or self.get_ocr_file_name(fpath)
        return [
            self.make_cmd("tesseract", fpath, dst.stem, "--psm", "1",  "-l", "eng"),
            self.make_cmd("mv", dst.with_suffix(".txt").name, dst)
            ]
