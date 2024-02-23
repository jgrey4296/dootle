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

import doot
import doot.errors
from doot._abstract import Action_p
from doot.mixins.importer import Importer_M
from doot.structs import DootKey, DootCodeReference

SPIDER  = DootKey.make("spider")
CRAWLER = DootKey.make("crawler")

class RunSpider(Action_p, Importer_M):
    """
      add a spider to the scrapy crawler that is in state
    """

    @DootKey.kwrap.expands("spider")
    @DootKey.kwrap.types("crawler")
    def __call__(self, spec, state, spider, crawler):
        spider_ref   = DootCodeReference.from_str(spider)
        spider_class = spider_ref.try_import()
        deferred     = crawler.crawl(spider_class)

        deferred.addCallback(lambda _: printer.warning("Crawl Complete"))
        printer.info("Crawler Started: %s", deferred)
        return deferred
