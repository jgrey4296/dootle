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
from string import Template

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKey, DKeyed
import doot
import doot.errors

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
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
            mapping[key_s] = DKey(key_s, implicit=True, mark=DKey.Mark.STR).expand(spec, state)

        match safe:
            case False:
                result = template.substitute(mapping)
            case _:
                result = template.safe_substtute(mapping)

        return { _update: result }
