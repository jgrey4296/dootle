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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from string import Template

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import doot.errors
from doot.structs import DKey, DKeyed

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class TemplateExpansion:
    """
      Expand string templates
    """

    @DKeyed.types("template", check=str|Template)
    @DKeyed.types("safe", fallback=False)
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, template, safe, _update):
        match template:
            case str():
                template = Template(template)
            case Template():
                pass

        # Expand kwargs first
        mapping = {}
        for key_s in template.get_identifiers():
            mapping[key_s] = DKey(key_s, implicit=True).expand(spec, state)

        match safe:
            case False:
                result = template.substitute(mapping)
            case _:
                result = template.safe_substtute(mapping)

        return { _update: result }
