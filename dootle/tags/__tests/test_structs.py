#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

logging = logmod.root

from dootle.tags.structs import TagFile, NameFile, SubstitutionFile, IndexFile

class TestTagFile:

    def test_initial(self):
        obj = TagFile()
        assert(obj is not None)

    @pytest.mark.parametrize("tag,exp", [("tag", "tag"), ("a tag", "a_tag"), ("A Tag", "A_Tag")])
    def test_norm_tag(self, tag, exp):
        obj = TagFile()
        normed = obj.norm_tag(tag)
        assert(normed == exp)

    def test_empty(self):
        obj = TagFile()
        assert(not bool(obj))

    def test_non_empty(self):
        obj = TagFile({"blah": 1})
        assert(bool(obj))

    def test_len(self):
        obj = TagFile({"blah": 1})
        assert(len(obj) == 1)

    def test_len_2(self):
        obj = TagFile({"blah": 1, "bloo": 3})
        assert(len(obj) == 2)

    def test_contains(self):
        obj = TagFile({"blah": 1})
        assert("blah" in obj)

    def test_contains_fail(self):
        obj = TagFile({"blah": 1})
        assert("bloo" not in obj)

    def test_contains_norms(self):
        obj = TagFile({"a blah": 1, "a_bloo":5})
        assert("a blah" in obj)
        assert("a_blah" in obj)
        assert("a_bloo" in obj)
        assert("a bloo" in obj)

    def test_update_str(self):
        obj = TagFile()
        assert(not bool(obj))
        assert("bloo" not in obj)
        obj.update("bloo")
        assert(bool(obj))
        assert("bloo" in obj)

    def test_update_list(self):
        obj = TagFile()
        assert(not bool(obj))
        assert("bloo" not in obj)
        obj.update(["bloo", "blee"])
        assert(bool(obj))
        assert("bloo" in obj)

    def test_update_set(self):
        obj = TagFile()
        assert(not bool(obj))
        obj.update({"bloo", "blah", "blee"})
        assert(bool(obj))
        assert("bloo" in obj)
        assert("blah" in obj)
        assert("blee" in obj)

    def test_update_str_multi(self):
        obj = TagFile()
        assert(not bool(obj))
        assert("bloo" not in obj)
        obj.update("bloo", "blah")
        assert(bool(obj))
        assert("bloo" in obj)
        assert("blah" in obj)

    def test_update_dict(self):
        obj = TagFile()
        assert(not bool(obj))
        obj.update({"bloo":1, "blah":3, "blee":5})
        assert(bool(obj))
        assert("bloo" in obj)
        assert("blah" in obj)
        assert("blee" in obj)

    def test_update_tagfile(self):
        obj = TagFile()
        obj2 = TagFile({"blah":1, "bloo":1, "blee":1})
        assert(not bool(obj))
        obj.update(obj2)
        assert(bool(obj))
        assert("bloo" in obj)
        assert("blah" in obj)
        assert("blee" in obj)

    def test_to_set(self):
        obj = TagFile({"blah":1, "bloo":1, "blee":1})
        as_set = obj.to_set()
        assert(isinstance(as_set, set))
        assert(len(as_set) == 3)

    def test_get_count(self):
        obj = TagFile({"blah":1, "bloo":5, "blee":1})
        assert(obj.get_count("blah") == 1)

    def test_get_count_2(self):
        obj = TagFile({"blah":1, "bloo":5, "blee":1})
        assert(obj.get_count("bloo") == 5)

    def test_get_count_missing(self):
        obj = TagFile({"blah":1, "bloo":5, "blee":1})
        assert(obj.get_count("aweg") == 0)

    def test_count_inc(self):
        obj = TagFile({"blah":1, "bloo":5, "blee":1})
        assert(obj.get_count("bloo") == 5)
        obj.update("bloo")
        assert(obj.get_count("bloo") == 6)

    def test_str(self):
        obj = TagFile({"blah":1, "bloo":5, "blee":1, "aweg": 0})
        assert(str(obj) == "\n".join(["blah : 1", "blee : 1", "bloo : 5"]))

class TestSubFile:

    def test_initial(self):
        obj = SubstitutionFile()
        assert(obj is not None)

    def test_len(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(len(obj) == 3)

    def test_sub_default(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(obj.sub("a") == {"a"})

    def test_sub_norms(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(obj.sub("a tag") == {"a_tag"})
        assert(obj.sub("a_tag") == {"a_tag"})

    def test_update_just_count(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(obj.get_count("b") == 5)
        obj.update("b")
        assert(obj.get_count("b") == 6)

    def test_update_subs(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(obj.sub("a_tag") == {"a_tag"})
        obj.update(("a tag", 1, "blah"))
        assert(obj.sub("a_tag") == {"blah"})


    def test_contains(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert("a tag" in obj)
        assert("a_tag" in obj)


    def test_contains_subs(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert("a tag" in obj)
        assert("a_tag" in obj)
        obj.update(("a tag", 1, "blah"))
        assert("blah" in obj)


    def test_subs_dont_have_subs(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        obj.update(("a tag", 1, "blah"))
        assert("blah" in obj)
        assert(not obj.has_sub("blah"))


    def test_has_sub_false(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(not obj.has_sub("a"))
        assert(not obj.has_sub("a_tag"))

    def test_has_sub_on_norm(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(obj.has_sub("a tag"))
        assert(not obj.has_sub("a_tag"))

    def test_has_sub_true(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(not obj.has_sub("a_tag"))
        obj.update(("a_tag", 1, "blah"))
        assert(obj.has_sub("a tag"))


    def test_update_multi_sub(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        assert(not obj.has_sub("a_tag"))
        obj.update(("a_tag", 1, "blah", "bloo"))
        assert(obj.sub("a_tag") == {"blah", "bloo"})


    def test_canonical(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        obj.update(("a_tag", 1, "blah", "bloo"))
        canon = obj.canonical()
        assert(isinstance(canon, TagFile))
        assert("a" in canon)
        assert("b" in canon)
        assert("blah" in canon)
        assert("bloo" in canon)


    def test_canonical_filters_presubs(self):
        obj = SubstitutionFile({"a": 2, "b": 5, "a tag": 19})
        obj.update(("a_tag", 1, "blah", "bloo"), ("bloo", 1, "aweg"))
        canon = obj.canonical()
        assert(isinstance(canon, TagFile))
        assert("a_tag" not in canon)
        assert("bloo" not in canon)
        assert("aweg" in canon)

class TestIndexFile:

    def test_initial(self):
        pass

class TestNameFile:

    def test_initial(self):
        pass
