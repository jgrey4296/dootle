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

import doot
from doot import globber, tasker

##-- end imports

from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.json import JsonMixin

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import JsonParser
from typing import List

class JsonFormatTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin, JsonMixin):
    """
    ([data] -> data) Lint Json files with jq *inplace*
    """

    def __init__(self, name="json::format.inplace", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_file() and fpath.suffix in self.exts:
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        task.update({
            "uptodate" : [False],
            "actions" : [
                self.make_cmd(self.json_filter, [fpath], save="formatted"),
                (self.write_to, [fpath, "formatted"]),
                ],
            })
        return task



class JsonMixin:

    def json_load(self, fpath):
        return json.loads(fpath.read_text())

    def json_new_parser(self):
        return JsonParser(context=XmlContext())

    def json_load_using_gencode(self, fpath, parser, root_object=None, is_list=False):
        target_type = List[root_object] if is_list else root_object
        return parser.parse(filename, target_type)

    def json_filter(self, target, filter_str="."):
        """
        outputs to process' stdout
        """
        return ["jq", "-M", "S", filter_str, target]

    def json_schema(self, target, package="genJson"):
        """ writes output to stdout """
        args = ["xsdata", "generate",
                ("--recursive" if target.is_dir() else ""),
                "-p", package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                target
            ]

        return list(filter(bool, args))

    def json_plantuml(self, dst, src):
        """
        writes to dst
        """
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)

    def xsdata_generate(self, targets:list, package:str):
        """ TODO import and call xsdata directly
        using targets as URI's, into an xsdata.codegen.transformer.SchemaTransformer
        """
        from xsdata.models.config import GeneratorConfig
        from xsdata.codegen.transformer import SchemaTransformer

        config                = GeneratorConfig.read(config_file)
        config.output.package = package

        transformer           = SchemaTransformer(config=config, print=stdout)
        uris                  = sorted(map(pl.Path.as_uri, targets))
        transformer.process(uris)
