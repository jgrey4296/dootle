#!/usr/bin/env python3
"""
A Runner that uses twisted's Reactor api
"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Self)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
import doot
import doot.errors
from doot.enums import ReportEnum, ActionResponseEnum as ActRE
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i, ReportLine_i, Action_p
from doot.utils.signal_handler import SignalHandler
from doot.structs import DootTaskSpec, DootActionSpec
from doot.control.base_runner import BaseRunner, logctx

from zope.interface import implementer
from twisted.internet import reactor, protocol, defer, threads
from twisted.internet.interfaces import IStreamServerEndpoint

from scrapy.crawler import CrawlerRunner
import scrapy

dry_run                    = doot.args.on_fail(False).cmd.args.dry_run()
head_level    : Final[str] = doot.constants.printer.DEFAULT_HEAD_LEVEL
build_level   : Final[str] = doot.constants.printer.DEFAULT_BUILD_LEVEL
action_level  : Final[str] = doot.constants.printer.DEFAULT_ACTION_LEVEL
sleep_level   : Final[str] = doot.constants.printer.DEFAULT_SLEEP_LEVEL
execute_level : Final[str] = doot.constants.printer.DEFAULT_EXECUTE_LEVEL

reactor_timeout = doot.config.on_fail(2, int).settings.tasks.reactor_timeout()

@doot.check_protocol
class DootleReactorRunner(BaseRunner, TaskRunner_i):
    """ The simplest reactor task runner
      https://stackoverflow.com/questions/8532131

     wraps steps of running jobs/tasks/actions into deferreds
    """

    def __init__(self:Self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy=None):
        super().__init__(tracker=tracker, reporter=reporter, policy=policy)
        scrapy_settings           = dict(doot.config.scrapy.settings.items())
        self.crawler              = CrawlerRunner(settings=scrapy_settings)
        self.reactor              = reactor
        self._enter_msg = "---------- Reactor Starting ----------"
        self._exit_msg  = "---------- Reactor Finished ----------"

    def __call__(self, *tasks:str):
        """ Queues _run_next_task and starts the reactor """
        self.tracker.queue_task(*tasks)
        reactor.callWhenRunning(self._run_next_task)
        reactor.run()

    def _run_next_task(self):
        d = threads.deferToThread(self.tracker.next_for)
        d.pause()
        d.addCallback(self._handle_task)
        d.addCallback(self._handle_task_success)
        d.addErrback(self._handle_failure)

        d.addCallback(self._schedule_next)
        d.unpause()

    def _handle_task(self, task) -> defer.Deferred[None|Task]:
        printer.setLevel("INFO")
        match task:
            case None:
                logging.debug("Task is None")
                return None
            case Job_i():
                self.step += 1
                return defer.maybeDeferred(self._expand_job, task)
            case Task_i():
                self.step += 1
                return defer.maybeDeferred(self._execute_task, task)
            case _:
                raise doot.errors.DootTaskError("Unknown Task Base: %s", task, task=task)

    def _handle_failure(self, failure) -> defer.Failure:
        match failure:
            case doot.errors.DootTaskInterrupt():
                breakpoint()
                return failure
            case doot.errors.DootTaskTrackingError() as err:
                return err.task
            case doot.errors.DootTaskFailed() as err:
                printer.warning("Task Failed: %s : %s", err.task.name, err)
                self.tracker.update_state(err.task, self.tracker.state_e.FAILED)
                return err.task
            case doot.errors.DootTaskError() as err:
                printer.warning("Task Error : %s : %s", err.task.name, err)
                self.tracker.update_state(err.task, self.tracker.state_e.FAILED)
                return err.task
            case doot.errors.DootError() as err:
                printer.warning("Doot Error : %s", err)
                return failure
            case _:
                return failure

    def _schedule_next(self, task) -> defer.Deferred:
        """ Schedules the next available task """
        if task is None and not bool(self.tracker.task_queue):
            printer.info("Scheduling Reactor shutdown")
            return self.reactor.callLater(reactor_timeout, self.reactor.stop)

        if task is None:
            printer.info("Task is none, tracker is: %s", bool(self.tracker.task_queue))
            return self.reactor.callLater(reactor_timeout, self.reactor.stop)

        with logctx(task.spec.print_levels.on_fail(sleep_level).sleep()):
            sleep_len = task.spec.extra.on_fail(self.default_SLEEP_LENGTH, int|float).sleep()
            printer.info("[Sleeping (%s)...]", sleep_len, extra={"colour":"white"})
            return self.reactor.callLater(sleep_len, self._run_next_task)


    def _expand_job(self, job:Job_i) -> Job_i:
        """ turn a job into all of its tasks, including teardowns """
        logmod.debug("-- Expanding Job %s: %s", self.step, job.name)
        with logctx(job.spec.print_levels.on_fail(head_level).head()) as p:
            p.info("---- Job %s: %s", self.step, job.name, extra={"colour":"magenta"})
            if bool(job.spec.actions):
                p.warning("-- Job %s: Actions were found in job spec, but jobs don't _run_next_task actions")

        with logctx(job.spec.print_levels.on_fail(build_level).build()):
            count = 0
            for task in job.make():
                match task:
                    case Job_i():
                        printer.warning("Jobs probably shouldn't build jobs: %s : %s", str(job.name), str(task.name))
                        self.tracker.add_task(task, no_root_connection=True)
                        self.tracker.queue_task(task.name)
                    case Task_i():
                        self.tracker.add_task(task, no_root_connection=True)
                        self.tracker.queue_task(task.name)
                    case DootTaskSpec():
                        self.tracker.add_task(task, no_root_connection=True)
                        self.tracker.queue_task(task.name)
                    case _:
                        raise doot.errors.DootTaskError("Job %s Built a Bad Value: %s", str(job.name), task, task=str(job.name))

                count += 1

        logmod.debug("-- Job %s Expansion produced: %s tasks", job.name, count)
        return job

    def _execute_task(self, task:Task_i) -> defer.Deferred[Task]:
        """ execute a single task's actions """
        with logctx(task.spec.print_levels.on_fail(head_level).head()) as p:
            p.info("---- Task %s: %s", self.step, task.name, extra={"colour":"magenta"})

        d = defer.succeed(task)
        d.pause()
        action_count = 0
        action_result = ActRE.SUCCESS
        with logctx(task.spec.print_levels.on_fail(build_level).build()) as p:
            for action in task.actions:
                match action:
                    case DootActionSpec() if action.fun is None:
                        raise doot.errors.DootTaskError("Task %s Failed: Produced an action with no callable: %s", task.name, action, task=task.spec)
                    case DootActionSpec():
                        match self._execute_action(action_count, action, task):
                            case ActRE.SKIP:
                                action_result = ActRE.SKIP
                            case defer.Deferred() as x:
                                d.addCallback(lambda _: x)
                            case _:
                                pass
                    case _:
                        raise doot.errors.DootTaskError("Task %s Failed: Produced a bad action: %s", task.name, action, task=task.spec)

                action_count += 1
                if action_result is ActRE.SKIP:
                    p.info("------ Remaining Task Actions skipped by Action Instruction")
                    break

            else: # Only try to add more tasks if the actions completed successfully, and weren't skipped
                for new_task in task.maybe_more_tasks():
                    p.warning("Skipping task sub: %s", new_task)

            p.debug("------ Task Executed %s Actions", action_count)
            d.addCallback(lambda _: task)
            d.unpause()
        return d

    def _execute_action(self, count, action, task) -> ActRE|defer.Deferred:
        """ Run the given action of a specific task  """
        if dry_run:
            logging.info("Dry Run: Not executing action: %s : %s", task.name, action, extra={"colour":"cyan"})
            return ActRE.SUCCESS

        logmod.debug("------ Executing Action %s: %s for %s", count, action, task.name)
        result = None
        with logctx(task.spec.print_levels.on_fail(action_level).action()) as p:
            task.state['_action_step'] = count
            p.info("------ Action %s.%s: %s", self.step, count, action.do, extra={"colour":"cyan"})
            p.debug("------ Action %s.%s: args=%s kwargs=%s. state keys = %s", self.step, count, action.args, dict(action.kwargs), list(task.state.keys()))
            action.verify(task.state)
            task.state['_reactor'] = self.reactor
            task.state['_crawler'] = self.crawler

            with logctx(task.spec.print_levels.on_fail(execute_level).execute()):
                result = action(task.state)

            p.debug("-- Action Result: %s", result)

        match result:
            case defer.Deferred():
                pass
            case ActRE.SKIP:
                pass
            case None | True:
                result = ActRE.SUCCESS
            case dict():
                task.state.update(result)
                result = ActRE.SUCCESS
            case False | ActRE.FAIL:
                raise doot.errors.DootTaskFailed("Task %s Action Failed: %s", task.name, action, task=task.spec)
            case _:
                raise doot.errors.DootTaskError("Task %s Action %s Failed: Returned an unplanned for value: %s", task.name, action, result, task=task.spec)

        action.verify_out(task.state)

        logmod.debug("------ Action Execution Complete: %s for %s", action, task.name)
        return result
