##-- imports
"""
https://relaxng.org/jclark/
xmlschema, xsdata, xsdata-plantuml, generateDS
http://www.davekuhlman.org/generateDS.html
https://pyxb.sourceforge.net/
https://xmlschema.readthedocs.io/en/latest/
https://github.com/tefra/xsdata-plantuml
https://python-jsonschema.readthedocs.io/en/stable/
"""
from __future__ import annotations

import pathlib as pl
import shutil
import shlex
from functools import partial
from itertools import cycle

from itertools import cycle, chain

import logging as logmod
##-- end imports

printer = logmod.getLogger("doot._printer")

import sh
import pandas as pd

from lxml import etree
import resource
import xml.sax
import doot
import doot.errors
from doot.structs import DootKey, DootCodeReference
from doot._abstract import Action_p

FROM_K = DootKey.build("from")
UPDATE = DootKey.build("update_")
HANDLER = DootKey.build("handler")
ERRORS  = DootKey.build("errors")

xsdata_defaults = [ "--relative-imports", "--postponed-annotations", "--kw-only", "--frozen", "--no-unnest-clases", "--output", "dataclasses"]

def xml_elements(spec, state):
    # http://xmlstar.sourceforge.net/
    # cmd = sh.xml("el", "-u", target)
    return

def xml_trang(spec, state):
    """
    outputs to dst
    trang  : https://relaxng.org/jclark/ [-C catalogFileOrUri] [-I rng|rnc|dtd|xml] [-O rng|rnc|dtd|xsd] [-i input-param] [-o output-param] inputFileOrUri ... outputFile
    """
    # cmd = sh.trang(target, dest)
    return

def xml_xsd(spec, state):
    # cmd = sh.xsd(target, "/o", dst)
    return

def make_xsdata_config(spec, state):
    if pl.Path(".xsdata.xml").exists():
        return None
    sh.xsdata("init-config")
    return

def xml_xsdata(spec, state):
    """ xsdata : https://github.com/tefra/xsdata """
    xsdata_args = xsdata_defaults
    # sh.xsdata("generate", "--package", dst, *xsdata_args, target)
    return

def xml_plantuml(spec, state):
    """
    outputs to process' stdout
    """
    # sh.xsdata("generate", "-o", "plantuml", "-pp", target)
    return

def xml_format(spec, state):
    """
    outputs to process' stdout
    """
    args = ["-s", "4",     # indent 4 spaces
            "-R",          # Recover
            "-N",          # remove redundant declarations
            "-e", "utf-8", # encode in utf-8
    ]
    if target.suffix in [".html", ".xhtml", ".htm"]:
            args.append("--html")

    sh.xml.fo(*args)
    return

def xml_validate(spec, state):
    """
    outputs to process' stdout
    """
    args = ["-e",    # verbose errors
            "--net", # net access
            "--xsd"  # xsd schema
            ]
    sh.xml.val(*args)
    return

def stream_xml(spec, state):
    update_k                                        = UPDATE.redirect(spec)
    source                                          = FROM_K.to_path(spec, state)
    handler_ref : DootCodeReference[DootSaxHandler] = DootCodeReference.from_str(HANDLER.expand(spec, state))
    handler_cls                                     = handler_ref.try_import()
    handler                                         = handler_cls(spec, state)
    parser                                          = xml.sax.make_parser()

    errors = ERRORS.expand(spec, state)
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, True)
    printer.info("Starting to read")
    with source.open(errors=errors) as f:
        parser.parse(f)
    printer.info("Finished Read")

    return { update_k : handler }

class DootSaxHandler(xml.sax.handler.ContentHandler):
    """ xml.sax stream parsing from
    https://stackoverflow.com/questions/7693535/what-is-a-good-xml-stream-parser-for-python
    """

    def __init__(self, spec, state):
        pass

    def startDocument(self):
        pass

    def endDocument(self):
        pass

    def startElement(self, name, attrs):
        printer.info("Entering: %s", name)
        pass

    def endElement(self, name):
        printer.info("Exiting: %s", name)
        pass

    def characters(self, content):
        printer.info("Got Characters: %s", content)
        pass
