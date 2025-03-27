#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from math import inf
from uuid import UUID, uuid1
import subprocess

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.dkey import DKey, DKeyed
from jgdv.structs.chainguard import ChainGuard
import doot
import doot.errors
import mastodon
from doot._abstract import Task_p
from doot.structs import ActionSpec

# ##-- end 3rd party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

TOOT_SIZE            : Final[int]                   = doot.config.on_fail(250, int).mastodon.toot_size()
TOOT_IMAGE_SIZE      : Final[str]                   = doot.config.on_fail(9_000_000, int).mastodon.image_size()
RESOLUTION_RE        : Final[re.Pattern]            = re.compile(r".*?([0-9]+x[0-9]+)")
TOOT_IMAGE_TYPES     : Final[list[str]]             = [".jpg", ".png", ".gif"]
MAX_MASTODON_SIZE    : Fina[int]                    = 5_000_000
try:
    RESOLUTION_BLACKLIST : Final[pl.Path]               = doot.locs.image_blacklist
except AttributeError:
    RESOLUTION_BLACKLIST : Final[pl.Path]               = doot.locs["imgblacklist"]
##--|
class MastodonSetup:
    """ Default Mastodon Setup, using secrets from doot.locs.mastodon_secrets
      loads the secrets as a chainguard, and accesses mastodon.access_token and mastodon.url
      ensures thers an "image_temp" location
    """
    _instance : ClassVar[Maybe[mastodon.Mastodon]] = None

    @DKeyed.redirects("mastodon")
    @DKeyed.paths("mastodon_secrets")
    def __call__(self, spec, state, _data_key, _secrets) -> dict:
        if MastodonSetup._instance is None:
            doot.report.trace("---------- Initialising Mastodon", extra={"colour": "green"})
            secrets = ChainGuard.load(_secrets)
            MastodonSetup._instance = mastodon.Mastodon(
                access_token = secrets.mastodon.access_token,
                api_base_url = secrets.mastodon.url,
            )
            doot.locs.ensure("image_temp", task=state['_task_name'])
        else:
            doot.report.detail("Reusing Instance")

        return { _data_key : MastodonSetup._instance }

class MastodonPost:
    """ Default Mastodon Poster  """

    @DKeyed.types("mastodon", check=mastodon.Mastodon)
    @DKeyed.formats("from", "toot_desc")
    @DKeyed.paths("toot_image")
    def __call__(self, spec, state, _instance, _text, _image_desc, _image_path) -> bool:

        try:
            if _image_path.exists():
                return self._post_image(_instance, _text, _image_path, _image_desc)
            else:
                return self._post_text(_instance, _text)
        except mastodon.MastodonAPIError as err:
            general, errcode, form, detail = err.args
            resolution                     = RESOLUTION_RE.match(detail) if detail else None
            if resolution and resolution in self.resolution_blacklist:
                pass
            elif errcode == 422 and form == "Unprocessable Entity" and resolution:
                with RESOLUTION_BLACKLIST.open('a') as f:
                    f.write("\n" + resolution[1])

            doot.report.error("Mastodon Resolution Failure: %s", repr(err))
            return False
        except Exception as err:  # noqa: BLE001
            doot.report.error("Mastodon Post Failed: %s", repr(err))
            return False

    def _post_text(self, _instance, text) -> bool:
        doot.report.trace("Posting Text Toot: %s", text)
        if len(text) >= TOOT_SIZE:
            doot.report.warn("Resulting Toot too long for mastodon: %s\n%s", len(text), text)
            return False

        result = _instance.status_post(text)
        return True

    def _post_image(self, _instance, text, _image_path, _image_desc) -> bool:
        doot.report.trace("Posting Image Toot")

        assert(_image_path.exists()), f"File Doesn't Exist {_image_path}"
        assert(_image_path.stat().st_size < TOOT_IMAGE_SIZE), "Image to large, needs to be smaller than 8MB"
        assert(_image_path.suffix.lower() in TOOT_IMAGE_TYPES), "Bad Type, needs to be a jpg, png or gif"

        media_id = _instance.media_post(str(_image_path), description=_image_desc)
        _instance.status_post(text, media_ids=media_id)
        logging.debug("Image Toot Posted")
        return True

    def _handle_resolution(self, task) -> None:
        # post to mastodon
        with RESOLUTION_BLACKLIST.open('r') as f:
            resolution_blacklist = {x.strip() for x in f.readlines()}

        min_x, min_y = inf, inf

        if bool(resolution_blacklist):
            min_x        = min(int(res.split("x")[0]) for res in resolution_blacklist)
            min_y        = min(int(res.split("x")[1]) for res in resolution_blacklist)

        res : str    = self._get_resolution(task.selected_file)
        res_x, res_y = res.split("x")
        res_x, res_y = int(res_x), int(res_y)
        if res in resolution_blacklist or (min_x <= res_x and min_y <= res_y):
            logging.warning("Image is too big %s: %s", task.selected_file, res)

    def _get_resolution(self, filepath:pl.Path) -> str:
        # TODO replace with sh
        result = subprocess.run(["file", str(filepath)], capture_output=True, shell=False, check=False)
        if result.returncode == 0:
            res = RESOLUTION_RE.match(result.stdout.decode())
            return res[1]

        raise doot.errors.ActionError("Couldn't get image resolution", filepath, result.stdout.decode(), result.stderr.decode())

    def _maybe_compress_file(self, task) -> dict|bool:
        image = task.values['image']
        logging.debug("Attempting compression of: %s", image)
        assert(isinstance(task.filepath, pl.Path) and task.filepath.exists())
        ext               = task.filepath.suffix
        conversion_target = doot.locs.image_temp.with_suffix(ext)
        convert_cmd = self.make_cmd(["convert", str(task.filepath),
                                    *task.conversion_args,
                                    str(conversion_target)])
        convert_cmd.execute()

        if doot.locs.image_temp.stat().st_size < MAX_MASTODON_SIZE:
            return { 'image': doot.locs.image_temp }

        return False
