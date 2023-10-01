#!/usr/bin/env python3
"""

"""

##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
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

printer = logmod.getLogger("doot._printer")

import bibtexparser as b
import doot
from doot._abstract.task import Action_p
from doot.actions.base_action import DootBaseAction
from dootle.utils.bibtex.writer import DootleBibtexWriter
from doot.utils.tex import latex
from bibtexparser.bparser import BibTexParser

__all__ = []

NEWLINE_RE                 : Final[re.Pattern] = re.compile(r"\n+\s*")

default_convert_exclusions : Final[list]       = ["file", "url", "ID", "ENTRYTYPE", "_FROM_CROSSREF", "doi", "crossref", "tags", "look_in", "note", "reference_number", "see_also"]
convert_exclusions         : Final[list]       = doot.config.on_fail(default_convert_exclusions, list).bibtex.convert_exclusions()

class _OverrideDict(dict):
    """
    A Simple dict that doesn't error if a key isn't found.
    Used to avoid UndefinedString Exceptions in bibtex parsing
    """

    def __getitem__(self, k):
        if k not in self:
            logging.warning("Adding string to override dict: %s", k)
            self[k] = k
        return k

class BibtexInitAction(Action_p):
    """
      Initialise a bibtex database. Override 'entry_transform' for customisation of loading.

      pass a callable as the spec.args value tto use in stead of entry_transform
    """

    def __call__(self, spec, task_state_copy:dict):
        if 'database' in task_state_copy:
            return True

        db                   = b.bibdatabase.BibDatabase()
        db.strings           = _OverrideDict()
        bparser              = self._make_parser(spec)
        bparser.bib_database = db
        return { "database" : db }


    def entry_transform(self, entry) -> dict:
        """
          Transform for each bibtex entry on load
          by default, ensures everything is unicode
        """
        for k,v in entry.items():
            if 'url' in k or 'file' in k:
                continue
            entry[k] = NEWLINE_RE.sub(" ", latex.to_unicode(v))
        entry['__as_unicode'] = True
        return entry

    def _make_parser(self, spec):
        bparser = BibTexParser(common_strings=False)
        bparser.customization             = [spec.args or [self.entry_transform]][0]
        bparser.ignore_nonstandard_types  = spec.kwargs.on_fail(False, bool).ignore_nonstandard()
        bparser.homogenise_fields         = spec.kwargs.on_fail(False, bool).homogenise()
        bparser.expect_multiple_parse     = spec.kwargs.on_fail(True, bool).muli_parse()
        bparser.add_missing_from_crossref = spec.kwargs.on_fail(True, bool).crossref()
        bparser.alt_dict = spec.kwargs.on_fail({
            'authors'  : u'author',
            'editors'  : u'editor',
            'urls'     : u'url',
            'link'     : u'url',
            'links'    : u'url',
            'subjects' : u'subject',
            'xref'     : u'crossref',
            "school"   : "institution",
        }, dict).alt_dict()
        return bparser


class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a shared database """

    def __call__(self, spec, task_state_copy:dict):
        try:
            file_list            = task_state_copy.get('load_files') or spec.kwargs.load_files
            db                   = task_state_copy['database']

            for x in file_list:
                printer.info("Loading bibtex: %s", x)
                text = pl.Path(x).expanduser().read_bytes().decode("utf-8", "replace")
                bparser.parse(text, partial=True)
            printer.info("Bibtex loaded: %s entries", len(db.entries))

            if len(file_list) == 1:
                return {"current_year": pl.Path(file_list[0]).stem}

            return True
        except UnicodeDecodeError as err:
            printer.error("Unicode Error in File: %s, Start: %s", x, err.start)
            return False
        except Exception as err:
            printer.error("Bibtex File Loading Errored: %s : %s", x, err)
            return False

class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """

    def __call__(self, spec, task_state_copy):
        db     = task_state_copy['database']
        writer = DootleBibtexWriter()
        result = writer.write(self.current_db)
        return { "text": result }

class BibtexEntryTransformer(Action_p):
    """
      Run a transform over all entries of the database.
      By default, preps for conversion to str with BibtexToStrAction

      pass a callable in the spec to use that instead
      The callable modifies the entry *in place*
    """

    def __call__(self, spec, task_state_copy):
        lib_root = task_state_copy.get('lib_root', None) or spec.kwargs.on_fail(None).lib_root or doot.locs.bibtex_lib_root
        db       = task_state_copy['database']
        # TODO use spec.args[0] if callable else self.entry_transform
        transform = (spec.args or [self.entry_transform])[0]
        assert(callable(transform))
        for entry in db.entries:
            transform(entry, lib_root)

        return True

    def entry_transform(self, entry, lib_root) -> None:
        """ convert processed __{field}'s into strings in {field},
        removing the the __{field} once processed
        """

        delete_fields = set()
        if "_FROM_CROSSREF" in entry:
            delete_fields.update(entry.get('_FROM_CROSSREF', []))
            delete_fields.add('_FROM_CROSSREF')

        for field in sorted(entry.keys()):
            match field:
                case _ if any([x in field for x in convert_exclusions]):
                    pass
                case "__tags":
                    delete_fields.add(field)
                    entry["tags"] = self._join_tags(entry[field])
                case "__paths" if bool(entry['__paths']):
                    delete_fields.add(field)
                    entry.update(self._path_strs(entry[field], lib_root))
                case "__author" | "__editor" if bool(entry[field]):
                    delete_fields.add(field)
                    entry[field.replace("__","")] = self._flatten_names(entry[field])
                case _ if "__" in field:
                    delete_fields.add(field)
                case _:
                    try:
                        entry[field] = latex.to_latex(entry[field])
                    except AttributeError as err:
                        raise AttributeError(f"Failed converting {field} to unicode: {entry}", *err.args) from err

        for field in delete_fields:
            if field == 'author' or field == "year":
                continue
            del entry[field]

    def _flatten_names(self, names:list[dict]) -> str:
        """ join names to  {von} Last, {Jr,} First and... """
        result = []
        for person in names:
            if not bool(person):
                continue
            parts = []
            parts.append(" ".join(person['von']).strip())
            parts.append(" ".join(person['last']).strip() + ("," if bool(person['first']) else ""))
            if bool(person['jr']):
                parts.append(" ".join(person['jr']).strip() + ",")

            parts.append(" ".join(person['first']).strip())
            result.append(" ".join(parts).strip())

        final = " and ".join(result)
        return final

    def _join_tags(self, tagset) -> str:
        if not bool(tagset):
            return "__untagged"
        return ",".join(sorted(tagset))

    def _path_strs(self, pathdict, lib_root) -> dict:
        results = {}
        for field, path in pathdict.items():
            if not path.resolve().is_relative_to(lib_root):
                results[field] = str(path)
                continue

            assert(field not in results)
            rel_path = path.relative_to(lib_root)
            results[field] = str(rel_path)

        return results
