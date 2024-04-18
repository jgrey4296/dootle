#!/usr/bin/env python3
"""
Utility class for working with tag files
"""
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as logmod
import re
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

##-- end imports

logging = logmod.getLogger(__name__)

TAG_NORM : Final[re.Pattern] = re.compile(" +")

@dataclass
class TagFile:
    """ A Basic TagFile holds the counts for each tag use """

    counts : dict[str, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    sep    : str            = field(default=" : ")
    ext    : str            = field(default=".tags")

    norm_regex : re.Pattern  = TAG_NORM

    @classmethod
    def read(cls, fpath:pl.Path, sep=None) -> TagFile:
        obj = cls(sep=sep or cls.sep)
        for i, line in enumerate(fpath.read_text().split("\n")):
            try:
                obj.update(tuple(x.strip() for x in line.split(obj.sep)))
            except Exception as err:
                logging.warning("Failure Tag Read: (l:%s) : %s : %s : (file: %s)", i, err, line, fpath)

        return obj

    def __post_init__(self):
        orig = self.counts
        self.counts = defaultdict(lambda: 0)
        self.counts.update({self.norm_tag(x):y for x,y in orig.items()})

    def __iter__(self):
        return iter(self.counts)

    def __str__(self):
        """
        Export the counts, 1 entry per line, as:
        `key` : `value`
        """
        all_lines = []
        for key in sorted(self.counts.keys(), key=lambda x: x.lower()):
            if not bool(self.counts[key]):
                continue
            all_lines.append(self.sep.join([key, str(self.counts[key])]))
        return "\n".join(all_lines)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    def __iadd__(self, values:TagFile|str|dict|set):
        """  merge tags, updating their counts as well. """
        return self.update(values)

    def __len__(self):
        return len(self.counts)

    def __contains__(self, value):
        return self.norm_tag(value) in self.counts

    def _inc(self, key, *, amnt=1) -> None|str:
        norm_key = self.norm_tag(key)
        if not bool(norm_key):
            return None
        self.counts[norm_key] += amnt
        return norm_key

    def update(self, *values:str|TagFile|set|dict):
        for val in values:
            match val:
                case None | "":
                    continue
                case str():
                    self._inc(val)
                case list() | set():
                    self.update(*val)
                case dict():
                    self.update(*val.items())
                case (str() as key, int()|str() as counts):
                    self._inc(key, amnt=int(counts))
                case TagFile():
                    self.update(*val.counts.items())
        return self

    def to_set(self) -> Set[str]:
        return set(self.counts.keys())

    def get_count(self, tag):
        return self.counts[self.norm_tag(tag)]

    def norm_tag(self, tag):
        return self.norm_regex.sub("_", tag.strip())

class NameFile(TagFile):

    def norm_tag(self, tag):
        return tag

@dataclass
class SubstitutionFile(TagFile):
    """ SubstitutionFiles add a replacement tag for some tags """

    ext           : str                  = field(default=".sub")
    substitutions : Dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def __str__(self):
        """
        Export the substitutions, 1 entry per line, as:
        `key` : `counts` : `substitution`
        """
        all_lines = []
        for key in sorted(self.counts.keys()):
            if not bool(self.substitutions[key]):
                continue
            line = [key, str(self.counts[key])]
            line += sorted(self.substitutions[key])
            all_lines.append(self.sep.join(line))

        return "\n".join(all_lines)

    def __getitem__(self, key) -> set[str]:
        return self.sub(key)

    def canonical(self) -> TagFile:
        """ create a tagfile of just canonical tags"""
        # All substitutes are canonical
        canon = {x:1 for x in iter(self) if not self.has_sub(x)}
        return TagFile(canon)

    def sub(self, value:str) -> set[str]:
        """ apply a substitution if it exists """
        normed = self.norm_tag(value)
        if bool(self.substitutions.get(normed, None)):
            return self.substitutions[normed]

        return set([normed])

    def has_sub(self, value):
        normed = self.norm_tag(value)
        if normed != value:
            return True
        return bool(self.substitutions.get(normed, None))

    def update(self, *values:str|Tuple|dict|SubstitutionFile|TagFile|set):
        for val in values:
            match val:
                case None | "": # empty line
                    continue
                case str(): # just a tag
                    self._inc(val)
                case list() | set():
                    for key in val:
                        self._inc(key)
                case dict(): # tag and count
                    for key, val in val.items():
                        self._inc(key, amnt=val)
                case (str() as key, int() | str() as counts): # tag and count
                    self._inc(key, amnt=int(counts))
                case (str() as key, int() | str() as counts, *subs):
                    norm_key  = self._inc(key, amnt=int(counts))
                    norm_subs = [normed for x in subs if (normed:=self.norm_tag(x)) is not None]
                    self.update({x:1 for x in norm_subs}) # Add to normal counts too
                    self.substitutions[norm_key].update(norm_subs)
                case SubstitutionFile():
                    self.update(val.counts)
                    for tag, subs in val.substitutions.items():
                        self.substitutions[tag].update(subs)
                case TagFile():
                    self.update(val.counts.items())

        return self

@dataclass
class IndexFile(TagFile):
    """ Utility class for index file specification and writing """

    mapping : Dict[str, Set[pl.Path]] = field(default_factory=lambda: defaultdict(set))
    ext     : str                 = field(default=".index")

    def __iadd__(self, value) -> IndexFile:
        return self.update(value)

    def __str__(self):
        """
        Export the mapping, 1 key per line, as:
        `key` : `len(values)` : ":".join(`values`)
        """
        key_sort = sorted(list(self.mapping.keys()))
        total = [self.sep.join([k, str(self.counts[k])]
                               + sorted(str(y) for y in self.mapping[k]))
                 for k in key_sort]
        return "\n".join(total)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    def update(self, *values):
        for val in values:
            match val:
                case (str() as key, maybecount, *rest):
                    paths = set(pl.Path(x) for x in rest)
                    try:
                        count = int(maybecount)
                    except ValueError:
                        paths.add(pl.Path(count))
                        count = len(paths)

                    norm_key = self._inc(key, amnt=count)
                    self.mapping[norm_key].update(paths)
                case _:
                    raise TypeError("Unexpected form in index update", val)

        return self

    def files_for(self, *values, op="union"):
        the_files = None
        match op:
            case "union":
                fn = lambda x, y: x & y
            case "diff":
                fn = lambda x, y: x | y
            case "xor":
                fn = lambda x, y: x ^ y
            case "rem":
                fn = lambda x, y: x - y
            case _:
                raise TypeError("Bad Op specified: ", op)

        for val in values:
            match the_files:
                case None if val in self.mapping:
                    the_files = self.mapping[val]
                case None:
                    continue
                case {} if op != "union":
                    return the_files
                case _:
                    the_files = fn(the_files, self.mapping[val])

        return the_files
