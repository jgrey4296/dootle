#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from os import system
from os.path import split
from typing import (Any, Callable, ClassVar, Dict, Final, Generic, Iterable,
                    Iterator, List, Mapping, Match, MutableMapping, Optional,
                    Sequence, Set, Tuple, TypeVar, Union, cast)
##-- end imports

logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")

import requests
import doot
import doot.errors
from doot.structs import DootKey
from doot import job
from doot._abstract import Action_p

CHECK_AMNT    : Final[int] = doot.config.on_fail(150, int).downloader.check_amnt()
speak_confirm : Final      = "Found a Large Group of Files, waiting for confirmation"

URL                        = DootKey.make("url")
TO                         = DootKey.make("to")

def download_media(spec, state):
    """ Download all media mentioned in json files """
    print("Downloading media %s to: %s" % (len(media), media_dir))
    target = TO.to_path(spec, state)
    source = URL.expand(spec, state)
    if not target.exists():
        target.mkdir()
    assert(target.is_dir())
    download_to(target, [source])

def download_to(fpath:pl.Path, urls:list):
    remaining = [x for x in urls if x is not None and not (fpath / pl.Path(x).name).exists()]

    if len(remaining) > CHECK_AMNT:
        speak_confirm.execute()
        result = input("Continue? [y/n] ")
        if result != "y":
            print("Skipping download")
            return

    scaler = int(len(urls) / 100) + 1
    for i, x in enumerate(urls):
        if i % scaler == 0:
            print("%s/100" % int(i/scaler))

        filename = fpath / split(x)[1]
        if filename.exists():
            continue

        try:
            request = requests.get(x)
            with open(filename, 'wb') as f:
                f.write(request.content)
        except Exception as e:
            logging.warning("Error Downloading: %s", x)
            logging.warning(str(e))
