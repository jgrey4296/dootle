#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
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

import doot
from doot.control.tasker import DootTasker
from doot.mixins.human import HumanMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

log_fmt     : Final[list] = doot.config.on_fail(["%aI", "%h", "%al", "%s"], list).git.fmt()
default_sep : Final[str]  = doot.config.on_fail(" :: ", str).git.sep()
group_hours : Final[int]  = doot.config.on_fail(2, int).git.group_by_hours()
bar_fmt     : Final[str]  = doot.config.on_fail("~", str).git.bar_fmt()
bar_max     : Final[int]  = doot.config.on_fail(40, int).git.bar_max()


class GitLogTask(DootTasker, CommanderMixin, FilerMixin):
    """
    ([root] -> temp) Output a summary of the git repo, with a specific format
    see: https://git-scm.com/docs/git-log
    """

    def __init__(self, name="report::git.raw", locs:DootLocData=None, fmt:list[str]=None, sep:str=default_sep):
        super().__init__(name, locs)
        self.format = fmt or log_fmt
        self.sep    = sep
        self.locs.ensure("temp", task=name)

    def task_detail(self, task):
        target = self.locs.temp / "full_git.log"
        task.update({
            "actions" : [ self.make_cmd(self.get_log, save="result"),
                          (self.write_to, [target, "result"]),
                         ],
            "targets" : [ target ],
            "clean"   : True,
        })
        return task

    def get_log(self):
        log_format = self.sep.join(self.format)
        return ["git", "log", f"--pretty=format:{log_format}"]


class GitLogAnalyseTask(DootTasker, HumanMixin):
    """
    (temp -> build) separate the printed log
    """

    def __init__(self, name="report::git", locs=None, sep=default_sep):
        super().__init__(name, locs)

        # Data extracted from logs:
        self.totals        = []
        self.entry_count   = 0
        self.sep           = sep
        self.group_by      = datetime.timedelta(hours=group_hours)
        self.grouped_total = 0
        self.year_max      = None
        self.year_min      = None
        self.times         = defaultdict(lambda: 0)
        self.weekday_times = defaultdict(lambda: 0)
        self.weekdays      = defaultdict(lambda: 0)
        self.days          = defaultdict(lambda: 0)
        self.day_times     = defaultdict(lambda: 0)
        self.months        = defaultdict(lambda: 0)
        self.month_days    = defaultdict(lambda: 0)
        self.month_times   = defaultdict(lambda: 0)

        # Deltas in Days:
        self.deltas        = defaultdict(lambda: 0)
        self.update_tuples = [(self.times         , "%H:%M"),
                              (self.weekday_times , "%w: %H:%M (%a)"),
                              (self.weekdays      , "%w (%a)"),
                              (self.days          , "%d"),
                              (self.day_times     , "%d: %H:%M"),
                              (self.months        , "%m (%b)"),
                              (self.month_days    , "%m %d (%b)"),
                              (self.month_times   , "%m : %H:%M (%b)"),
                              ]
        # streaks / breaks
        # weekends / weekdays
        # day / night
        # tags
        # files touched
        self.locs.ensure("build", "temp", task=name)

    def task_detail(self, task):
        task.update({
            "targets"  : [ self.locs.build / "git.report" ],
            "file_dep" : [ self.locs.temp / "full_git.log"],
            "actions"  : [
                self.read_log,
                self.process_log,
                self.write_distributions,
            ],
        })
        return task

    def read_log(self, dependencies):
        """
        Read the log file line by line, and prepare it for extraction
        """
        last = None
        linecount = 0
        for line in pl.Path(dependencies[0]).read_text().split("\n"):
            linecount += 1
            if not bool(line.strip()):
                continue
            parts = line.split(self.sep)

            assert(len(parts) == 4), linecount
            commit : datetime = self.round_time(datetime.datetime.fromisoformat(parts[0]), roundTo=60*60)
            self.totals.append(commit)

    def process_log(self):
        """
        With all information loaded, extract information from the commits
        """
        self.totals.sort()
        self.entry_count = len(totals)
        for commit in totals:
            if self.year_max is None:
                self.year_max = commit.year
            else:
                self.year_max = max(self.year_max, commit.year)
            if self.year_min is None:
                self.year_min = commit.year
            else:
                self.year_min = min(self.year_min, commit.year)

            # Deltas:
            diff = None
            if last is not None:
                diff = max(last, commit) - min(last, commit)
                self.deltas[diff.days] += 1

            last = commit
            if diff is not None and diff < self.group_by:
                continue

            self.grouped_total += 1
            for fmt, targ in self.update_tuples:
                targ[commmit.strftime(fmt)] += 1


    def write_distributions(self, targets):
        """
        Finally write the information into a report
        """
        with open(targets[0], 'w') as f:
            print(f"Git Report", file=f)
            print(f"Total commits: {self.entry_count}", file=f)
            print(f"With at least a day in between commits: {self.grouped_total}", file=f)
            print(f"Covering {self.year_min} - {self.year_max}", file=f)
            print("----------", file=f)
            print("", file=f)

            for name, data in zip(["times", "times by weekday", "weekday", "days of the month", "times by day of month", "month", "day by month", "time by month", "time between activity (to nearest day)"],
                                  [self.times, self.weekday_times, self.weekdays, self.days, self.day_times, self.months, self.month_days, self.month_times, self.deltas]):
                print("", file=f)
                print("----------", file=f)
                print(name, file=f)
                print("----------", file=f)
                print("", file=f)
                max_count = max(data.values())
                norm = bar_max / max_count
                for x,y in sorted(data.items()):
                    bar = bar_fmt * int(y * norm)
                    print(f"{x:>4} = {y:>7} |{bar}", file=f)
