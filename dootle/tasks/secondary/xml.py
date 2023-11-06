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


from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.xml import XMLMixin


class XmlValidateTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin, XMLMixin):
    """
    ([data]) Validate xml's by schemas
    """

    def __init__(self, name="xml::validate", locs:DootLocData=None, roots:list[pl.Path]=None, rec=False, xsd=None):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml", ".xhtml", ".htm"], rec=rec)
        self.xsd = xsd
        if self.xsd is None:
            raise Exception("For Xml Validation you need to specify an xsd to validate against")

    def set_params(self):
        return self.target_params() + [
            {"name":"xsd", "long":"xsd", "type": pl.Path, "default": None}
            ]

    def filter(self, fpath):
        if self.args['xsd'] is None:
            return self.globc.no

        if fpath.is_file() and fpath.suffix in self.exts:
            return self.globc.yes

        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        if self.args['xsd'] is None:
            return None

        task.update({
            "actions" : [ self.make_cmd(self.xml_validate, fpath, self.args['xsd'])]
        })
        return task

class XmlFormatTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin, XMLMixin):
    """
    ([data] -> data) Basic Formatting with backup
    """

    def __init__(self, name="xml::format", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".xml", ".xhtml", ".html"], rec=rec)
        self.locs.ensure("temp", task='xml::format')

    def set_params(self):
        return self.target_params() + [
            {"name": "in-place", "long": "in-place", "type": bool, "default": False}
        ]

    def filter(self, fpath):
        if fpath.is_file() and fpath.suffix in self.exts:
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        out_target = fpath if self.args['in-place'] else self.locs.temp / "xml_formatted" / fpath.name

        task.update({
            'actions': [
                self.make_cmd(self.xml_format, fpath, save="formatted"),
                (self.write_to, [out_target, "formatted"]),
            ]
        })
        return task



"""


"""
