"""


"""
##-- imports
from __future__ import annotations

import abc
import collections.abc
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
##-- end imports

INSTANCE_KEY         : Final[str]                   = "mastodon"
TEXT_KEY             : Final[str]                   = "text"
IMAGE_KEY            : Final[str]                   = "image"
IMAGE_DESC           : Final[str]                   = "desc"
