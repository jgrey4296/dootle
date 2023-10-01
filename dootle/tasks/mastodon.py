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
# from bs4 import BeautifulSoup
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
import more_itertools as mitz
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import spacy # nlp = spacy.load("en_core_web_sm")
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import mastodon
import tomler
import doot
import doot.errors
from doot._abstract import Task_i
from doot.enums import StructuredNameEnum
from doot.structs import DootActionSpec

from doot.task.base_task import DootTask

toot_size            : Final[int]                   = doot.config.on_fail(250, int).mastodon.toot_size()
toot_image_size      : Final[str]                   = doot.config.on_fail("8mb", str).mastodon.image_size()
RESOLUTION_BLACKLIST : Final[list]                  = doot.locs.image_blacklist

RESOLUTION_RE        : Final[re.Pattern]            = re.compile(r".*?([0-9]+x[0-9]+)")

INSTANCE_KEY         : Final[str]                   = "mastodon"
TEXT_KEY             : Final[str]                   = "text"
IMAGE_KEY            : Final[str]                   = "image"
IMAGE_DESC           : Final[str]                   = "desc"

def example_text(task_state_copy:dict):
    return {TEXT_KEY: "this is a test post, ignore it"}

def config_text(spec:Tomler, task_state_copy:dict):
    return {TEXT_KEY: spec.args[0]}



class MastodonPoster(DootTask, Task_i):
    """
      A standardised task for posting to mastodon,
      sandwiches config specified actions between a setup action and a post action
    """
    mastodon : mastodon.Mastodon
    resolution_blacklist : set() = set()

    @property
    def actions(self):
        yield DootActionSpec(fun=self.setup_mastodon)
        yield from super().actions
        yield DootActionSpec(fun=self.post)

    def setup_mastodon(self, task_state_copy):
        printer.info("---------- Initialising Mastodon", extra={"colour": "green"})
        secrets = tomler.load(pl.Path(doot.locs.mastodon_secrets).expanduser())
        instance = mastodon.Mastodon(
            access_token = secrets.mastodon.access_token,
            api_base_url = secrets.mastodon.url
        )
        doot.locs.ensure("image_temp", task=self.name)
        return {INSTANCE_KEY: instance}

    def post(self, task_state_copy):
        if not INSTANCE_KEY in task_state_copy:
            return False

        try:
            match task_state_copy:
                case { "image" : pl.Path() }:
                    return self._post_image(task_state_copy)
                case { "text" : str() }:
                    return self._post_text(task_state_copy)
                case _:
                    raise doot.errors.DootTaskError("Unknown Mastodon Posting type")

        except mastodon.MastodonAPIError as err:
            general, errcode, form, detail = err.args
            resolution = RESOLUTION_RE.match(detail) if detail else None
            if resolution and resolution in self.resolution_blacklist:
                pass
            elif errcode == 422 and form == "Unprocessable Entity" and resolution:
                with open(RESOLUTION_BLACKLIST, 'a') as f:
                    f.write("\n" + resolution[1])

            printer.error("Mastodon Resolution Failure: %s", repr(err))
            return False
        except Exception as err:
            printer.error("Mastodon Post Failed: %s", repr(err))
            return False

    def _post_text(self, task_state_copy):
        printer.info("Posting Text Toot")
        instance = task_state_copy[INSTANCE_KEY]
        msg      = task_state_copy.get(TEXT_KEY, "")
        if len(msg) >= toot_size:
            printer.warning("Resulting Toot too long for mastodon: %s\n%s", len(msg), msg)
            return False

        result = instance.status_post(msg)
        return True

    def _post_image(self, task_state_copy):
        printer.info("Posting Image Toot")
        # 8MB
        instance    = task_state_copy[INSTANCE_KEY]
        msg         = task_state_copy.get(TEXT_KEY, "")
        desc        = task_state_copy.get(IMAGE_DESC, "")
        the_file    = pl.Path(task_state_copy[IMAGE_KEY]).expanduser()
        # if the_file.stat().st_size > 8_000_000:
        # the_file = compress_file(the_file)

        assert(the_file.exists()), f"File Doesn't Exist {the_file}"
        assert(the_file.stat().st_size < 8_000_000), "Bad Size"
        assert(the_file.suffix.lower() in [".jpg", ".png", ".gif"]), "Bad Type"

        media_id = instance.media_post(str(the_file), description=desc)
        # media_id = instance.media_update(media_id, description=desc)
        instance.status_post(msg, media_ids=media_id)
        logging.debug("Image Toot Posted")
        return True

    def _handle_resolution(self, task):
        # post to mastodon
        with open(RESOLUTION_BLACKLIST, 'r') as f:
            resolution_blacklist = {x.strip() for x in f.readlines()}

        min_x, min_y = inf, inf

        if bool(resolution_blacklist):
            min_x        = min(int(res.split("x")[0]) for res in resolution_blacklist)
            min_y        = min(int(res.split("x")[1]) for res in resolution_blacklist)

        res : str    = _get_resolution(selected_file)
        res_x, res_y = res.split("x")
        res_x, res_y = int(res_x), int(res_y)
        if res in resolution_blacklist or (min_x <= res_x and min_y <= res_y):
            logging.warning("Image is too big %s: %s", selected_file, res)
            return

    def _get_resolution(self, filepath:Path) -> str:
        result = subprocess.run(["file", str(filepath)], capture_output=True, shell=False)
        if result.returncode == 0:
            res = RESOLUTION_RE.match(result.stdout.decode())
            return res[1]

        raise Exception("Couldn't get image resolution", filepath, result.stdout.decode(), result.stderr.decode())

    def _maybe_compress_file(self, task):
        image = task.values['image']
        logging.debug("Attempting compression of: %s", image)
        assert(isinstance(filepath, pl.Path) and filepath.exists())
        ext               = filepath.suffix
        conversion_target = doot.locs.image_temp.with_suffix(ext)
        convert_cmd = self.make_cmd(["convert", str(filepath),
                                    *conversion_args,
                                    str(conversion_target)])
        convert_cmd.execute()

        if doot.locs.image_temp.stat().st_size < 5000000:
            return { 'image': doot.locs.image_temp }

        return False

"""

"""
