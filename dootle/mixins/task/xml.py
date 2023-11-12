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

##-- end imports

from doot import dir_walker, tasker



class XMLMixin:

    xsdata_defaults = [ "--relative-imports",
                       "--postponed-annotations",
                       "--kw-only",
                       "--frozen",
                       "--no-unnest-clases",
                       "--output", "dataclasses"]
    element_arg     = "-u"

    def xml_elements(self, *targets):
        """
        ouputs to process' stdout
        build an `xml el` command of all available xmls
        http://xmlstar.sourceforge.net/
        """
        target_files = []
        dir_glob = (lambda x: self.glob_target(x, fn=lambda x: x.is_file())) if hasattr(self, "glob_target") else lambda x: x.rglob("*.xml")
        for fpath in targets:
            match fpath.is_file():
                case True:
                    target_files.append(fpath)
                case False:
                    target_files += list(dir_glob(fpath))

        return ["xml", "el", self.element_arg] + target_files

    def xml_trang(self, dst, targets:list):
        """
        outputs to dst
        trang  : https://relaxng.org/jclark/ [-C catalogFileOrUri] [-I rng|rnc|dtd|xml] [-O rng|rnc|dtd|xsd] [-i input-param] [-o output-param] inputFileOrUri ... outputFile
        """
        assert(all([x.suffix == ".xml" for x in targets])), "Trang only accepts .xml files"
        return ["trang"] + targets + [dst]

    def xml_xsd(self, dst, targets):
        """
        generates to dst
        xsd    : mono
        """
        return ["xsd"] + targets + ["/o", dst]

    def make_xsdata_config(self):
        if pl.Path(".xsdata.xml").exists():
            return None
        return self.cmd("xsdata", "init-config")

    def xml_xsdata(self, dst, target):
        """
        generates to fpath
        xsdata : https://github.com/tefra/xsdata
        """
        xsdata_args = and_args or self.xsdata_defaults
        return ["xsdata", "generate"] + ["--package", dst] + xsdata_args + [target]

    def xml_plantuml(self, target):
        """
        outputs to process' stdout
        """
        return ["xsdata", "generate", "-o", "plantuml", "-pp", target]

    def xml_format(self, target):
        """
        outputs to process' stdout
        """
        args = ["xml" , "fo",
            "-s", "4",     # indent 4 spaces
            "-R",          # Recover
            "-N",          # remove redundant declarations
            "-e", "utf-8", # encode in utf-8
        ]
        if target.suffix in [".html", ".xhtml", ".htm"]:
                args.append("--html")

        args.append(target)
        return args

    def xml_validate(self, targets:list, xsd:pl.Path):
        """
        outputs to process' stdout
        """
        args = ["xml", "val",
                "-e",    # verbose errors
                "--net", # net access
                "--xsd"  # xsd schema
                ]
        args.append(self.xsd)
        args += targets
        return args
