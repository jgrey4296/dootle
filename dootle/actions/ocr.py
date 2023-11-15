#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from typing import Final

from functools import partial
from itertools import cycle, chain
##-- end imports

logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
from doot._abstract import Action_p

import numpy as np
import PIL
from PIL import Image
from sklearn.cluster import KMeans

default_ocr_exts : Final[list] = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".ppm"]

default_pdf_exts : Final[list] = [".GIF", ".JPG", ".PNG", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".ppm"]

ocr_exts         : Final[list] = doot.config.on_fail(default_ocr_exts, list).images.ocr_exts()
ocr_out_ext      : Final[str] = doot.config.on_fail(".ocr", str).images.ocr_out()

framerate        : Final[int] = doot.config.on_fail(10, int).images.framerate()

THUMB            : Final[tuple] = (200,200)

ocr_out_ext      : Final[str] = doot.config.on_fail(".ocr", str).images.ocr_out()

HashImages = hashing.HashAllFiles

def load_img(path:pl.Path):
    try:
        img = Image.open(str(path))
        img2 = img.convert('RGB')
        return img2
    except:
        return None

def norm_img(img):
    split_c1 = img.split()
    histograms = [np.array(x.histogram()) for x in split_c1]
    sums = [sum(x) for x in histograms]
    norm_c1 = [x/y for x,y in zip(histograms, sums)]
    return np.array(norm_c1).reshape((1,-1))


@doot.check_protocol
class OCRAction(Action_p):

    def __call__(self, spec, state):
        pass

    def get_ocr_file_name(self, fpath):
        return fpath.parent / f".{fpath.stem}{ocr_out_ext}"

    def make_ocr_cmds(self, fpath, dst=None):
        """
        outputs to cwd dst.txt
        """
        dst = dst or self.get_ocr_file_name(fpath)
        return [
            self.make_cmd("tesseract", fpath, dst.stem, "--psm", "1",  "-l", "eng"),
            self.make_cmd("mv", dst.with_suffix(".txt").name, dst)
            ]
