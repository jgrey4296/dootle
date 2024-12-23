#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import base64
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
from doot.enums import ActionResponse_e
from doot.structs import DKey, DKeyed
from jgdv.files.bookmarks.collection import BookmarkCollection
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxService
from selenium.webdriver.common.print_page_options import PrintOptions

# ##-- end 3rd party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()

##-- end logging

FF_DRIVER     : Final[str] = "__$ff_driver"
READER_PREFIX : Final[str] = "about:reader?url="

def setup_firefox(spec, state):
    """ Setups a selenium driven, headless firefox to print to pdf """
    printer.info("Setting up headless Firefox")
    options = FirefoxOptions()
    # options.add_argument("--start-maximized")
    options.add_argument("--headless")
    # options.binary_location = "/usr/bin/firefox"
    # options.binary_location = "/snap/bin/geckodriver"
    options.set_preference("print.always_print_silent", True)
    options.set_preference("print.printer_Mozilla_Save_to_PDF.print_to_file", True)
    options.set_preference("print_printer", "Mozilla Save to PDF")
    options.set_preference("print.printer_Mozilla_Save_to_PDF.use_simplify_page", True)
    options.set_preference("print.printer_Mozilla_Save_to_PDF.print_page_delay", 50)
    service = FirefoxService(executable_path="/snap/bin/geckodriver")
    driver = Firefox(options=options, service=service)
    return { FF_DRIVER : driver }

@DKeyed.expands("url")
@DKeyed.paths("to")
@DKeyed.types(FF_DRIVER)
def save_pdf(spec, state, url, _to, _driver):
    """ prints a url to a pdf file using selenium """
    printer.info("Saving: %s", url)
    print_ops = PrintOptions()
    print_ops.page_range = "all"

    driver.get(READER_PREFIX + url)
    time.sleep(2)
    pdf       = _driver.print_page(print_options=print_ops)
    pdf_bytes = base64.b64decode(pdf)

    with open(_to, "wb") as f:
        f.write(pdf_bytes)

@DKeyed.types(FF_DRIVER)
def close_firefox(spec, state, _driver):
    printer.info("Closing Firefox")
    _driver.quit()
