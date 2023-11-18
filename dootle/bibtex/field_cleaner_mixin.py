#!/usr/bin/env python
"""
utilities for cleaning bibtex files
"""
##-- imports
from __future__ import annotations

import argparse
import logging as logmod
import pathlib as pl
from typing import Final
from dataclasses import InitVar, dataclass, field
from hashlib import sha256
from itertools import cycle
from math import ceil
from shutil import copyfile, move
from uuid import uuid4

import re
##-- end imports
from dootle.bibtex.writer import DootleBibtexWriter


##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

__all__ = ["BibFieldCleanMixin", "BibPathCleanMixin"]

from bibtexparser import customization as bib_customization

STEM_CLEAN_RE  : Final[re.Pattern] = re.compile(r"[^a-zA-Z0-9_]+")
UNDERSCORE_RE  : Final[re.Pattern] = re.compile(r"_+")
NEWLINE_RE     : Final[re.Pattern] = re.compile(r"\n+\s*")
AND_RE         : Final[re.Pattern] = re.compile(r"\ and\ ", flags=re.IGNORECASE)
TAGSPLIT_RE    : Final[re.Pattern] = re.compile(r",|;")
TITLESPLIT_RE  : Final[re.Pattern] = re.compile(r"^\s*(.+?): (.+)$")
TITLE_CLEAN_RE : Final[re.Pattern] = re.compile("[^a-zA-Z0-9]")

empty_match : Final[re.Match] = re.match("","")

class BibFieldCleanMixin:
    """
    mixin for cleaning fields of bibtex records
    """

    def bc_lowercase_keys(self, entry):
        uppercase = {x for x in entry.keys() if not (x.islower() or x.isupper()) }
        entry.update({x.lower(): entry.pop(x) for x in uppercase})

    def bc_match_year(self, entry, target, msg=None) -> None|tuple[str, str]:
        """
        check the year is the right one for the file its in
        """
        if 'year' not in entry:
            raise KeyError(f"Entry doesn't have a year: {entry}")
        if entry['year'] == target:
            return None

        return entry['ID'], msg.format(target=target, actual=entry['year'])

    def bc_title_split(self, entry):
        if 'title' not in entry:
            return entry
        if "subtitle" in entry:
            return entry

        match (TITLESPLIT_RE.match(entry['title']) or empty_match).groups():
            case ():
                pass
            case (title, subtitle):
                entry['__orig_title'] = entry['title']
                entry['title']        = (title[0].upper() + title[1:]).strip()
                entry['subtitle']     = (subtitle[0].upper() + subtitle[1:]).strip()

        return entry

    def bc_split_names(self, entry):
        """
        convert names to component parts, for authors and editors
        """
        match entry:
            case { "author" : "" }:
                logging.warning("Entry Has empty author: %s", entry['ID'])
                entry['author']        = "Anon"
                entry['__author']     = self._separate_names("Anon")
                entry['__split_names'] = "author"
            case { "editor" : "" }:
                logging.warning("Entry Has empty editor: %s", entry['ID'])
                entry['editor']        = "Anon"
                entry['__editor']     = self._separate_names("Anon")
                entry['__split_names'] = "editor"
            case { "author": author }:
                entry['__author'] = self._separate_names(author)
                entry['__split_names'] = "author"
            case { "editor" : editor }:
                entry['__editor']     = self._separate_names(editor)
                entry['__split_names'] = "editor"
            case _:
                logging.warning("Entry Has No author or editor: %s", entry['ID'])
                entry['author']        = "Anon"
                entry['__author']     = self._separate_names("Anon")
                entry['__split_names'] = "author"

        return entry

    def bc_tag_split(self, entry):
        """
        split raw tag strings into parts, clean and strip whitespace,
        then make them a set
        """
        tags_subbed     = NEWLINE_RE.sub("_", entry.get("tags", ""))
        tags            = TAGSPLIT_RE.split(tags_subbed)
        entry["__tags"] = {x.strip() for x in tags if bool(x.strip())}
        if not bool(entry["__tags"]):
            entry["__tags"].add("__untagged")
        return entry

    def _separate_names(self, text):
        try:
            names = AND_RE.split(text)
            result = [bib_customization.splitname(x.strip(), False) for x in names]
            return result
        except StopIteration:
            raise IndexError(f"Unbalanced curlys in {text}")
