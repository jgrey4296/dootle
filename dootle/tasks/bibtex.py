#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import itertools
import logging as logmod
import pathlib as pl
import re
import shutil
import sys
import time
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from os.path import commonpath
from re import Pattern
from string import Template
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
logmod.getLogger('bibtexparser').setLevel(logmod.CRITICAL)
##-- end logging

printer = logmod.getLogger("doot._printer")

import tomler
import doot
from doot.tasks.base_task import DootTask
from doot.structs import DootActionSpec

from dootle.actions.bibtex_io import BibtexInitAction, BibtexToStrAction, BibtexEntryTransformer
from dootle.utils.bibtex.field_cleaner import BibFieldCleanMixin
from dootle.utils.bibtex.path_cleaner import BibPathCleanMixin

clean_in_place       : Final[bool] = doot.config.on_fail(False, bool).bibtex.clean_in_place()
wayback_wait         : Final[int] = doot.config.on_fail(10, int).bibtex.wayback_wait()
acceptible_responses : Final[list] = doot.config.on_fail(["200"], list).bibtex.accept_wayback()
ENT_const            : Final[str] = 'ENTRYTYPE'

class BibtexBase(DootTask):

    @property
    def actions(self):
        yield BibtexInitAction(tomler.Tomler())
        yield from super().actions

class LibDirClean(FilerMixin):
    """
    Clean the directories of the bibtex library
    """

    def filter(self, fpath):
        if fpath.is_dir() and not bool(list(fpath.iterdir())):
            return self.globc.keep
        return self.globc.discard

    def actions(self, task_state_copy):
        yield DootActionSpec(fun=self.rmdirs)

class BibtexClean(BibFieldCleanMixin, BibPathCleanMixin, FilerMixin):
    """
    (src -> src) Clean all bib files
    formatting, fixing paths, etc
    """
    wrong_year_msg = " : Wrong Year: (Bibfile: {target}) != ({actual} : Entry)"
    bad_file_msg   = " : File Does Not Exist : {file}"

    def actions(self):
        yield DootActionSpec(fun=lambda x: {"target": task_state_copy['file'] if self.clean_in_place else self.locs.temp / task_state_copy['file'].name})
        yield DootActionSpec(fun=BibtexEntryTransformer, args=tomler.Tomler({"args": [self.on_parse_check_entry]}))
        yield DootActionSpec(fun=BibtexEntryTransformer, args=tomler.Tomler({"args": [self.loaded_clean_entry]}))

    def on_parse_check_entry(self, entry):
        # Preprocess
        self.bc_lowercase_keys(entry)
        self.bc_tag_split(entry)
        assert("__tags" in entry)

        if 'year' not in entry:
            entry['year'] = "2023"

        if 'school' in entry and 'institution' not in entry:
            entry['institution'] = entry['school']
            del entry['school']

        if entry['ENTRYTYPE'].lower() in ["phdthesis", "mastersthesis"]:
            entry['type'] = entry['ENTRYTYPE'].lower().replace("thesis","")
            entry['ENTRYTYPE'] = "thesis"

        # TODO store entry, add it to correct year
        match self.bc_match_year(entry, self.current_year, self.wrong_year_msg):
            case (e_id, msg) as err:
                print(e_id + msg, file=sys.stderr)
                self.issues.append(err)

        self.bc_expand_paths(entry, self.locs.pdfs)
        assert("__paths" in entry)
        for e_id, msg in self.bc_check_files(entry, self.bad_file_msg):
            self.issues.append((e_id, msg))
            logging.warning(e_id + msg)

    def loaded_clean_entry(self, entry):
        assert('crossref' not in entry or '_FROM_CROSSREF' in entry), entry
        self.bc_split_names(entry)
        self.bc_title_split(entry)
        self.bc_base_name(entry)
        self.bc_ideal_stem(entry)

        ##-- file path cleanup
        # Clean files [(field, orig, newloc, newstem)]
        movements : list[tuple[str, pl.Path, pl.Path, str]] = self.bc_prepare_file_movements(entry, self.locs.pdfs)
        orig_parents = set()
        for field, orig, new_dir, new_stem in movements:
            orig_parents.add(orig.parent)
            unique = self.bc_unique_stem(orig, (new_dir / new_stem).with_suffix(orig.suffix))
            if unique is None:
                continue

            if self.args['move-files'] and not new_dir.exists():
                new_dir.mkdir(parents=True)
            elif not new_dir.exists():
                logging.info("+ dir? : %s", new_dir)

            if self.args['move-files']:
                entry['__paths'][field] = orig.rename(unique)
            else:
                common = commonpath((orig, unique))
                logging.info("--- ")
                logging.info("|-  : %s", str(orig).removeprefix(common))
                logging.info("->  : %s", str(unique).removeprefix(common))
                logging.info("---")
        ##-- end file path cleanup

        ##-- parent path cleanup
        for parent in orig_parents:
            if not bool(list(parent.iterdir())):
                logging.info("Proposed Directory Cleanup: %s", parent)
            ##-- end parent path cleanup

class BibtexStub(DootTaask):
    """
    (src -> data) Create basic stubs for found pdfs and epubs
    """
    stub_t     = Template("@misc{stub_key_$id,\n  author = {},\n  title = {$title},\n  year = {$year},\n  file = {$file}\n}")

    def filter(self, fpath):
        if fpath.is_file() and fpath.name not in self.source_file_set:
            return self.globc.accept
        return self.globc.discard

    @properties
    def actions(self):
        yield DootActionSpec(fun=self.read_stub_contents)
        yield DootActionSpec(fun=self.move_to_workdir)
        yield DootActionSpec(fun=self.stub_all)

    def read_stub_contents(self, task_state_copy):
        if "existing_stubs" in task_state_copy:
            return True

        source_text     = self.locs.bib_stub_file.read_text()
        file_re         = re.compile(r"\s*file\s*=\s*{(.+)}")
        stub_re         = re.compile(r"^@.+?{stub_key_(\d+),$")
        stub_ids        = [0]
        source_file_set = set()
        for line in source_text.split("\n"):
            file_match = file_re.match(line)
            key_match  = stub_re.match(line)

            if key_match is not None:
                stub_ids.append(int(key_match[1]))

            if file_match is not None:
                source_file_set.add(pl.Path(file_match[1]).name)

        max_stub_id = max(stub_ids)
        logging.debug("Found %s existing stubs", len(source_file_set))
        return {"existing_stubs" : source_file_set}

    def move_to_workdir(self, task_state_copy):
        src = task_state_copy['target']
        dst = self.locs.bibtex_working / src.name
        if dst.exists():
            src.rename(src.with_stem(f"exists_{src.stem}"))
            return True

        shutil.move(str(src), str(dst))
        # src.rename(dst)
        return { "moved_to" : str(dst) }

    def stub_all(self, task_state_copy):
        task_state_copy['stubs'] = []
        wd    = self.locs.bibtex_working
        for fpath in itertools.chain(wd.glob("*.pdf"), wd.glob("*.epub")):
            if fpath.name in self.source_file_set:
                continue
            if fpath.name.startswith("_refiled"):
                continue

            self.max_stub_id += 1
            stub_str = BibtexStub.stub_t.substitute(id=self.max_stub_id,
                                                    title=fpath.stem,
                                                    year=datetime.datetime.now().year,
                                                    file=str(fpath.expanduser().resolve()))
            task_state_copy['stubs'].append(stub_str)

        if bool(task_state_copy['stubs']):
            self.append_stubs(task_state_copy)

        return True

    def append_stubs(self, task_state_copy):
        logging.info(f"Adding {len(self.stubs)} stubs")
        with open(self.locs.bib_stub_file, 'a') as f:
            f.write("\n")
            f.write("\n\n".join(task_state_copy['stubs']))

class BibtexWaybacker(BibFieldCleanMixin, WebMixin):
    """
    get all urls from bibtexs,
    then check they are in wayback machine,
    or add them to it
    then add the wayback urls to the relevant bibtex entry
    """

    def on_parse_check_entry(self, entry) -> dict:
        url_keys = [k for k in entry.keys() if "url" in k]
        if not bool(url_keys):
            return entry

        save_prefix = "https://web.archive.org/save"
        for k in url_keys:
            url = entry[k]
            match self.check_wayback(url):
                case None: # is wayback url? continue
                    pass
                case False: # create wayback url and replace
                    result = self.post_url(save_prefix, url=url)
                    recheck = self.check_wayback(url)
                    if isinstance(recheck, str):
                        entry[k] = recheck
                case str() as way_url: # wayback url exists? replace
                    entry[k] = way_url
                case _:
                    raise TypeError("Unknown wayback response")

        return entry

    def check_wayback(self, url) -> bool|str:
        if "web.archive.org" in url:
            return None
        time.sleep(wayback_wait)
        check_url = " http://archive.org/wayback/available?url=" + url
        json_data : dict = self.get_url(check_url)
        if 'archived_snapshots' not in json_data:
            return False

        closest = json_data['archived_snapshots'].get('closest', None)
        if closest is not None and closest['status'] in acceptible_responses and closest.get('available', False):
            return closest["url"]

class BibtexCompile():
    """
    Compile individual bibtex file into pdf
    """

    def actions(self):
        # config actions to sub filter
        pass
