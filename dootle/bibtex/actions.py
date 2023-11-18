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

import bibtexparser as b
import doot
from doot._abstract.task import Action_p
from doot.actions.base_action import DootBaseAction
from dootle.bibtex.writer import DootleBibtexWriter
from dootle.latex.utils import latex
from bibtexparser.bparser import BibTexParser
from doot.utils.string_expand import expand_str, expand_key, expand_to_obj, expand_set

printer = logmod.getLogger("doot._printer")

__all__ = []

NEWLINE_RE                 : Final[re.Pattern] = re.compile(r"\n+\s*")

default_convert_exclusions : Final[list]       = ["file", "url", "ID", "ENTRYTYPE", "_FROM_CROSSREF", "doi", "crossref", "tags", "look_in", "note", "reference_number", "see_also"]
convert_exclusions         : Final[list]       = doot.config.on_fail(default_convert_exclusions, list).bibtex.convert_exclusions()

DB_KEY                     : Final[str] = "bib_db"
UNIQ_DB_KEY                : Final[str] = "bib_uniq"
FILES_KEY                  : Final[str] = "bib_files"
STATE_KEY                  : Final[str] = "load_key"
TEXT_KEY                   : Final[str] = "bib_text"
LIB_ROOT_KEY               : Final[str] = "bib_root"
YEAR_KEY                   : Final[str] = "current_year"

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
      Initialise a bibtex database. Override '_entry_transform' for customisation of loading.

      pass a callable as the spec.args value to use instead of _entry_transform
    """

    def __call__(self, spec, task_state:dict):
        data_key = expand_str(spec.kwargs.on_fail(DB_KEY).update_(), spec, task_state)
        if data_key in task_state:
            return True

        db                   = b.bibdatabase.BibDatabase()
        db.strings           = _OverrideDict()
        printer.info("Bibtex Database Initialised")

        return { data_key : db }

class BibtexLoadAction(Action_p):
    """ Parse all the bibtext files into a task_state database, in place.

      addFn to task_state[`_entry_transform`] to use a custom entry transformer,
      or subclass this and override self._entry_transform.

      """
    _toml_kwargs = ["update_", "transform", "current_year", "ignore_nonstandard", "homogenise", "multi_parse", "crossref"]

    def __call__(self, spec, task_state:dict):
            year_key             = expand_str(spec.kwargs.on_fail(YEAR_KEY).year_(), spec, task_state)
            db_key               = expand_str(spec.kwargs.on_fail(DB_KEY).update_(), spec, task_state, as_key=True)
            from_key             = expand_str(spec.kwargs.on_fail("_from").from_(), spec, task_state, as_key=True)
            transform_key        = expand_str(spec.kwargs.on_fail("transform").transform_(), spec, task_state, as_key=True)

            file_list            = list(expand_set(from_key, spec, task_state, as_path=True))
            try:
                transform        = expand_to_obj(transform_key, spec, task_state)
            except KeyError:
                transform        = self._entry_transform

            db                   = expand_to_obj(db_key, spec, task_state)
            bparser              = self._make_parser(spec, db, transform)

            printer.info("Attempting to load files: %s", [str(x) for x in file_list])
            current_entry_count = len(db.entries)
            for loc in file_list:
                printer.info("Loading bibtex: %s", loc)
                try:
                    text = loc.read_bytes().decode("utf-8", "replace")
                    bparser.parse(text, partial=True)
                    printer.info("Loaded: %s entries",  len(db.entries) - current_entry_count)
                    current_entry_count = len(db.entries)
                except UnicodeDecodeError as err:
                    printer.error("Unicode Error in File: %s, Start: %s", loc, err.start)
                    return False
                except Exception as err:
                    printer.error("Bibtex File Loading Errored: %s : %s", loc, err)
                    return False


            printer.info("Total DB Entry Count: %s", current_entry_count)
            if len(file_list) == 1:
                loc = doot.locs[file_list[0]]
                printer.info("Current year: %s", loc.stem)
                return { year_key: loc.stem }

            return True

    def _make_parser(self, spec, db, transform=None):
        """
          Builds a bibtexparser with default settings
        """
        bparser = BibTexParser(common_strings=False)
        bparser.customization             = transform or self._entry_transform
        bparser.ignore_nonstandard_types  = spec.kwargs.on_fail(False, bool).ignore_nonstandard()
        bparser.homogenise_fields         = spec.kwargs.on_fail(False, bool).homogenise()
        bparser.expect_multiple_parse     = spec.kwargs.on_fail(True, bool).multi_parse()
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

        bparser.bib_database = db
        return bparser

    def _entry_transform(self, entry) -> dict:
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


class BibtexMergeAction(Action_p):

    _toml_kwargs                                         = ["clear", "update_", "from_"]
    shared_db : ClassVar[None|b.bibdatabase.BibDatabase] = None

    def __call__(self, spec, task_state):
        if BibtexMergeAction.shared_db is None or spec.kwargs.on_fail(False).clear():
            printer.info("Initialising Shared DB")
            BibtexMergeAction.shared_db         = b.bibdatabase.BibDatabase()
            BibtexMergeAction.shared_db.strings = _OverrideDict()

        db_key                                  = expand_str(spec.kwargs.on_fail(DB_KEY).from_(), spec, task_state, as_key=True)
        data_key                                = expand_str(spec.kwargs.on_fail(DB_KEY).update_(), spec, task_state)

        try:
            pre_count = len(BibtexMergeAction.shared_db.entries)
            db = expand_to_obj(db_key, spec, task_state)
            BibtexMergeAction.shared_db.entries += db.entries[:]
            post_count = len(BibtexMergeAction.shared_db.entries)
        except KeyError:
            printer.debug("No Database found at: %s", db_key)


        printer.info("Updated Entry Count: %s", len(BibtexMergeAction.shared_db.entries))
        return { data_key : BibtexMergeAction.shared_db}


class BibtexToStrAction(Action_p):
    """
      Convert a bib database to a string for writing to a file.
    """
    _toml_kwargs = ["from_", "update_"]


    def __call__(self, spec, task_state):
        db_key                                  = expand_str(spec.kwargs.on_fail(DB_KEY).from_(), spec, task_state, as_key=True)
        data_key                                = expand_str(spec.kwargs.on_fail(TEXT_KEY).update_(), spec, task_state)
        db                                      = expand_to_obj(db_key, spec, task_state)
        writer                                  = DootleBibtexWriter()
        result                                  = writer.write(db)
        return { data_key : result }

class BibtexEntryTransformer(Action_p):
    """
      Runs *IN PLACE*
      For each state key in spec.args,
      use that state value as a function to transform each entry.

      transforms should be of the form:
      def transform(entry:dict, spec, task_state) -> bool

      If a transform returns False, don't run any more transforms and remove that entry from the database

      By default, preps for conversion to str with BibtexToStrAction

      pass a callable in the spec to use that instead
      The callable modifies the entry *in place*
    """
    _toml_kwargs = ["from_"]

    def __call__(self, spec, task_state):
        db = expand_key(spec.kwargs.on_fail(DB_KEY).from_(), spec, task_state)
        match spec.args:
            case []:
                transforms = [self._entry_transform]
            case [*keys]:
                transforms = [task_state[key] for key in keys]

        assert(all(callable(x) for x in transforms))
        printer.debug("Transforming Entries with: %s", spec.args or "default")
        to_remove = set()
        for entry in db.entries:
            for transform in transforms:
                if not transform(entry, spec, task_state):
                    to_remove.add(entry)
                    break

        curr_count = len(db.entries)
        map(db.entries.remove, to_remove)
        reduced_count = len(db.entries)

        if reduced_count + len(to_remove) != curr_count:
            raise doot.errors.DootActionError("Amounts don't match for removing entries")

        return True

    def _entry_transform(self, entry, spec, task_state) -> None:
        """ convert processed __{field}'s into strings in {field},
        removing the the __{field} once processed
        """
        lib_root = task_state.get(LIB_ROOT_KEY, None) or spec.kwargs.on_fail(None)[LIB_ROOT_KEY] or doot.locs.bibtex_lib_root
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

        return True

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


class BibtexCompileAction(Action_p):
    """ Run bibtex on a location """

    def __call__(self, spec, task_state):
        raise NotImplementedError("TODO")
