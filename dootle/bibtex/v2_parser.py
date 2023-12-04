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

import bibtexparser
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware

import doot
from doot._abstract.task import Action_p
from dootle.bibtex import middlewares as dmids

# TODO library init
# TODO file parse
# TODO library merge - lib.add(entriesc]
# TODO library write - bibtexparser.write_string(lib, unparse_stack=stack, bibtex_format=format)

read_mids = [
    ms.ResolveStringReferencesMiddleware(True),
    ms.RemoveEnclosingMiddleware(True),
    ms.LatexDecodingMiddleware(True, keep_braced_groups=True, keep_math_mode=True),
    dmids.ParsePathsMiddleware(allow_parallel_execution=True, allow_inplace_modification=True),
    dmids.ParseTagsMiddleware(allow_parallel_execution=True, allow_inplace_modification=True),
    ms.SeparateCoAuthors(True),
    ms.SplitNameParts(True),
]

write_mids = [
    ms.MergeNameParts(True),
    ms.MergeCoAuthors(True),
    ms.LatexEncodingMiddleware(keep_math=True, enclose_urls=False),
    dmids.WriteTagsMiddleware(allow_parallel_execution=True, allow_inplace_modification=True),
    ms.AddEnclosingMiddleware(allow_inplace_modification=True, default_enclosing="{", reuse_previous_enclosing=False, enclose_integers=True),
]

format                 = bibtexparser.BibtexFormat()
format.value_column    = 15
format.indent          = " "
format.block_separator = "\n"
format.trailing_comma  = True


lib = bibtexparser.parse_file(target, parse_stack=read_mids)
assert(len(lib.failed_blocks) == 0)
bibtexparser.write_file(str(output), lib, parse_stack=write_mids, bibtex_format=format)

"""

"""
