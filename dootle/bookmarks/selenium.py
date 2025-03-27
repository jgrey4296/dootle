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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.files.bookmarks.collection import BookmarkCollection
from jgdv.structs.dkey import DKey, DKeyed

import doot
import doot.errors
from doot.enums import ActionResponse_e
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxService
from selenium.webdriver.common.print_page_options import PrintOptions

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

    from doot.structs import ActionSpec
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)

##-- end logging

FF_DRIVER     : Final[str] = "__$ff_driver"
READER_PREFIX : Final[str] = "about:reader?url="

def setup_firefox(spec:ActionSpec, state:dict) -> dict:
    """ Setups a selenium driven, headless firefox to print to pdf """
    doot.report.trace("Setting up headless Firefox")
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
    driver  = Firefox(options=options, service=service)
    return { FF_DRIVER : driver }

##--|
@DKeyed.expands("url")
@DKeyed.paths("to")
@DKeyed.types(FF_DRIVER)
def save_pdf(spec:ActionSpec, state:dict, url, _to, _driver) -> None:
    """ prints a url to a pdf file using selenium """
    doot.report.trace("Saving: %s", url)
    print_ops = PrintOptions()
    print_ops.page_range = "all"

    driver.get(READER_PREFIX + url)
    time.sleep(2)
    pdf       = _driver.print_page(print_options=print_ops)
    pdf_bytes = base64.b64decode(pdf)

    with _to.open("wb") as f:
        f.write(pdf_bytes)

@DKeyed.types(FF_DRIVER)
def close_firefox(spec:ActionSpec, state:dict, _driver) -> None:
    doot.report.trace("Closing Firefox")
    _driver.quit()
