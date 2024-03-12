#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial
import shlex

from functools import partial
from itertools import cycle, chain
##-- end imports

printer = logmod.getLogger("doot._printer")

import sh
import doot
import doot.errors
from doot._abstract import Action_p
from doot.structs import DootKey

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import JsonParser
from xsdata.models.config import GeneratorConfig
from xsdata.codegen.transformer import SchemaTransformer

FROM                = DootKey.build("from")
CONFIG              = DootKey.build("config")
TO                  = DootKey.build("to")
PACKAGE             = DootKey.build("package")
EXT                 = DootKey.build("ext")

def json_load(spec, state):
    source = FROM.to_path(spec, state)
    return json.loads(fpath.read_text())

def json_new_parser(self):
    return JsonParser(context=XmlContext())

def json_load_using_gencode(self, fpath, parser, root_object=None, is_list=False):
    target_type = list[root_object] if is_list else root_object
    return parser.parse(filename, target_type)

def json_filter(spec, state):
    """
    outputs to process' stdout
    """
    # return ["jq", "-M", "S", filter_str, target]
    return

def json_schema(spec, state):
    """ writes output to stdout """
    source = FROM.to_path(spec, state)
    pack = PACKAGE.expand(spec, state)
    args = [("--recursive" if source.is_dir() else ""),
            "-p", package,
            "--relative-imports", "--postponed-annotations",
            "--kw-only",
            "--frozen",
            "--no-unnest-classes",
            source
        ]
    sh.xsdata.generate(*args)
    return

def json_plantuml(self, dst, src):
    """
    writes to dst
    """
    source = FROM.to_path(spec, state)
    target = TO.to_path(spec, state)
    header   = "@startjson\n"
    footer   = "\n@endjson\n"

    with open(target, 'w') as f:
        f.write(header)
        f.write(source.read_text())
        f.write(footer)

    return

def xsdata_generate(spec, state):
    """ TODO import and call xsdata directly
    using targets as URI's, into an xsdata.codegen.transformer.SchemaTransformer
    """
    source                = FROM.to_path(spec, state)
    pack                  = PACKAGE.expand(spec, state)
    config_file           = CONFIG.to_path(spec, state)
    config                = GeneratorConfig.read(config_file)
    config.output.package = pack

    transformer           = SchemaTransformer(config=config, print=stdout)
    transformer.process(source.as_uri())
    return


def jsonlines_load(spec, state):
    raise NotImplementedError()

def jsonlines_append(spec, state):
    raise NotImplementedError()
