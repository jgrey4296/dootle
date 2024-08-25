#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import doot
import doot.errors
import mastodon
import tomlguard
from doot._abstract import Task_i
from doot.structs import DKey, DootActionSpec

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

TOOT_SIZE            : Final[int]                   = doot.config.on_fail(250, int).mastodon.toot_size()
TOOT_IMAGE_SIZE      : Final[str]                   = doot.config.on_fail(8_000_000, int).mastodon.image_size()
RESOLUTION_BLACKLIST : Final[list]                  = doot.locs.image_blacklist
RESOLUTION_RE        : Final[re.Pattern]            = re.compile(r".*?([0-9]+x[0-9]+)")
TOOT_IMAGE_TYPES     : Final[list[str]]             = [".jpg", ".png", ".gif"]

class MastodonSetup:
    """ Default Mastodon Setup, using secrets from doot.locs.mastodon_secrets
      loads the secrets as a tomlguard, and accesses mastodon.access_token and mastodon.url
      ensures thers an "image_temp" location
    """
    _instance = None

    DKeyed.redirects("mastodon")
    DKeyed.paths("mastodon_secrets")

    def __call__(self, spec, state, _data_key, _secrets) -> dict|bool|None:

        if MastodonSetup._instance is None:
            printer.info("---------- Initialising Mastodon", extra={"colour": "green"})
            secrets = tomlguard.load(_secrets)
            MastodonSetup._instance = mastodon.Mastodon(
                access_token = secrets.mastodon.access_token,
                api_base_url = secrets.mastodon.url
            )
            doot.locs.ensure("image_temp", task=state['_task_name'])
        else:
            printer.debug("Reusing Instance")

        return { _data_key : MastodonSetup._instance }

class MastodonPost:
    """ Default Mastodon Poster  """

    DKeyed.types("mastodon", check=Mastodon.Mastodon)
    DKeyed.formats("from", "toot_desc")
    DKeyed.paths("toot_image")
    DKeyed.format("toot_desc")

    def __call__(self, spec, state, _instance, _text, _image_desc, _image_path):

        try:
            if _image_path.exists():
                return self._post_image(_instance, text, _image_path, _image_desc)
            else:
                return self._post_text(_instance, text)
        except mastodon.MastodonAPIError as err:
            general, errcode, form, detail = err.args
            resolution                     = RESOLUTION_RE.match(detail) if detail else None
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

    def _post_text(self, _instance, text):
        printer.info("Posting Text Toot: %s", text)
        if len(text) >= TOOT_SIZE:
            printer.warning("Resulting Toot too long for mastodon: %s\n%s", len(text), text)
            return False

        result = _instance.status_post(text)
        return True

    def _post_image(self, _instance, text, _image_path, _image_desc):
        printer.info("Posting Image Toot")

        assert(_image_path.exists()), f"File Doesn't Exist {_image_path}"
        assert(_image_path.stat().st_size < TOOT_IMAGE_SIZE), "Image to large, needs to be smaller than 8MB"
        assert(_image_path.suffix.lower() in TOOT_IMAGE_TYPES), "Bad Type, needs to be a jpg, png or gif"

        media_id = _instance.media_post(str(_image_path), description=_image_desc)
        _instance.status_post(text, media_ids=media_id)
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

        raise doot.errors.DootActionError("Couldn't get image resolution", filepath, result.stdout.decode(), result.stderr.decode())

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
