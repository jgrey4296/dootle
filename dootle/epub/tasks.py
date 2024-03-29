
##-- imports
from __future__ import annotations

from typing import Final
import logging as logmod
import pathlib as pl
import re
import shutil
from collections import OrderedDict
from datetime import datetime
from importlib.resources import files
from os import environ
from string import Template
from uuid import uuid1
from bs4 import BeautifulSoup
##-- end imports

import doot
from doot.task import job, dir_walker
from doot.mixins.zipper import ZipperMixin

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- data
data_path           = files("doot.__templates")
title_template      = data_path / "epub_titlepage"
css_template        = data_path / "epub_css"
page_style_template = data_path / "epub_page_styles"
##-- end data

# https://www.w3.org/publishing/epub3/epub-packages.html
# https://www.w3.org/publishing/epub3/epub-spec.html#sec-cmt-supported

##-- epub templates
data_path      = files("doot.__templates")
MANIFEST_ENT_T = Template(data_path.joinpath("epub_manifest_entry").read_text())
MANIFEST_T     = Template(data_path.joinpath("epub_manifest").read_text())
SPINE_ENT_T    = Template(data_path.joinpath("epub_spine_entry").read_text())
NAV_T          = Template(data_path.joinpath("epub_nav").read_text())
NAV_ENT_T      = Template(data_path.joinpath("epub_nav_entry").read_text())
##-- end epub templates

ws : Final[re.Pattern] = re.compile("\s+")

class EbookGlobberBase(dir_walker.DootDirWalker):

    marker_file = ".epub"

    def filter(self, fpath):
        """ marker file exists? """
        if fpath.is_dir() and (fpath / self.marker_file ).exists():
            return self.control.keep
        return self.control.discard

class EbookCompileTask(EbookGlobberBase):
    """
    (GlobDirs: [src] -> build) convert directories to zips, then those zips to epubs
    """

    def __init__(self, name="epub::compile", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.locs.ensure("build", task=name)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ self.locs.build / fpath.with_suffix(".epub").name ]
        })
        return task

class EbookConvertTask(EbookGlobberBase):
    """
    (GlobDirs: [src, temp] -> build) *.zip -> *.epub

    TODO possibly only zips with the right contents
    """

    def __init__(self, name="_epub::convert.zip", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.locs.ensure("temp", "build", task=name)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.build / fpath.with_suffix(".epub").name ],
            "file_dep" : [ self.locs.temp / fpath.with_suffix(".zip").name ],
            "actions"  : [ self.make_cmd(self.action_convert) ],
            "clean"    : True,
        })
        return task

    def action_convert(self, dependencies, targets):
        return ["ebook-convert", dependencies[0], targets[0] ]

class EbookZipTask(EbookGlobberBase, ZipperMixin):
    """
    (GlobDirs: [src] -> temp) wrapper around ZipTask to build zips of epub directories
    """

    def __init__(self, name="_zip::epub", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.locs.ensure("temp", task=name)

    def subtask_detail(self, task, fpath=None):
        # TODO process the globs here, and exclude stuff
        zipf = self.locs.temp / fpath.with_suffix(".zip").name
        glob   = str(fpath) + "/**/*"

        task.update({
            "actions": [
                (self.zip_set_root, [fpath]),
                (self.zip_globs, [zipf, glob]),
            ],
            'task_dep': [ f"epub::manifest:{task['name']}"],
        })
        return task

class EbookManifestTask(EbookGlobberBase):
    """
    (GlobDirs: [src] -> src), Generate the manifest for an epub directory
    """

    def __init__(self, name="epub::manifest", locs:DootLocData=None, roots=None, rec=True, author=None):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        # Map path -> uuid
        self.uuids  = {}
        self.author = author or environ['USER']

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ fpath / "content.opf",
                           fpath / "content" / "nav.xhtml" ],
            "task_dep" : [ f"epub::restruct:{task['name']}" ]
        })
        task['actions'] += [ self.init_uuids,
                             self.backup,
                             self.generate_nav,
                             self.generate_manifest
                            ]
        return task

    def init_uuids(self):
        self.uuids.clear()

    def get_uuid(self, path):
        if str(path) in self.uuids:
            return self.uuids[str(path)]
        else:
            p_uuid =  path.stem + "_" + hex(uuid1().time_low)
            self.uuids[str(path)] = p_uuid
            return p_uuid

    def backup(self, targets):
        for targ in [pl.Path(x) for x in targets]:
            if targ.exists():
                targ.rename(targ.with_suffix(".backup"))

    def get_type_string(self, fpath):
        """
        from the epub3 spec
        """
        match fpath.suffix:
            case ".html" | ".xhtml" | ".htm":
                type_s = "application/xhtml+xml"
            case ".js":
                type_s = "application/javascript"
            case ".css" | ".xpgt":
                type_s = "text/css"
            case ".gif":
                type_s = "image/gif"
            case ".jpg" | ".jpeg":
                type_s = "image/jpeg"
            case  ".png":
                type_s = "image/png"
            case ".svg":
                type_s = "image/svg+xml"
            case ".ttf":
                type_s = "font/ttf"
            case ".oft":
                type_s = "font/oft"
            case ".woff":
                type_s = "font/woff"
            case ".woff2":
                type_s = "font/woff2"
            case _:
                print("Unrecogized file type when constructing manifest: ", fpath)
                raise Exception()

        return type_s

    def get_title(self, fpath):
        """
        Get the h1 or meta.title, of a an x/html file
        """
        assert(fpath.suffix in [".xhtml", ".html", ".htm"]), fpath.suffix
        soup = BeautifulSoup(fpath.read_text(), "html.parser")
        title = soup.h1
        if title is None:
            title = soup.title
        if title is None:
            title = "Default Title"

        return ws.sub(" ", title.text)

    def generate_nav(self, targets):
        """
        Generate nav content for nav.xhtml
        """
        nav     = pl.Path(targets[1])
        content = nav.parent
        assert(content.name == "content")
        entries = []
        for cont in content.glob("*"):
            if cont.suffix == ".backup":
                continue
            if cont.name[0] in ".":
                continue
            uuid  = self.get_uuid(cont)
            title = self.get_title(cont)
            entries.append(NAV_ENT_T.substitute(uuid=uuid,
                                                path=cont.relative_to(content),
                                                title=title).strip())

        nav.write_text(NAV_T.substitute(navs="\n".join(entries)))

    def generate_manifest(self, targets):
        """
        glob all files, construct the manifest from templates, write the file
        """
        manifest = pl.Path(targets[0])
        date_str = datetime.now().isoformat()
        epub_dir = manifest.parent
        assert(epub_dir.parent == self.locs.src)
        manifest_entries = []
        spine_entries    = []
        guide_entries    = []
        for path in epub_dir.glob("**/*"):
            if path.suffix in  [".backup", ".opf"]:
                continue
            if path.name[0] in ".":
                continue
            if path.is_dir():
                continue

            p_uuid = self.get_uuid(path)
            ext    = path.suffix
            try:
                type_s = self.get_type_string(path)
            except Exception:
                continue

            manifest_entries.append(MANIFEST_ENT_T.substitute(uuid=p_uuid,
                                                              path=path.relative_to(epub_dir),
                                                              type=type_s).strip())

            # TODO sort title -> nav -> rest
            if type_s == "application/xhtml+xml":
                spine_entries.append(SPINE_ENT_T.substitute(uuid=p_uuid).strip())

        expanded_template = MANIFEST_T.substitute(title=epub_dir.stem,
                                                  author_sort=self.author,
                                                  author=self.author,
                                                  uuid=uuid1().hex,
                                                  date=date_str,
                                                  manifest="\n".join(manifest_entries),
                                                  spine="\n".join(spine_entries)
                                                  )
        manifest.write_text(expanded_template)

class EbookRestructureTask(EbookGlobberBase):
    """
    (GlobDirs: [src] -> src) Reformat working epub locs to the same structure
    *.x?htm?              -> content/
    *.css                 -> style/
    *.jpg|gif|png|svg     -> image/
    *.ttf|otf|woff|woff2  -> font/
    """

    def __init__(self, name="epub::restruct", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], rec=rec)
        self.content_mapping : OrderedDict[str, re.Pattern] = OrderedDict((
            ("content", re.compile(".+(x?html?|js)")),
            ("style", re.compile(".+(css|xpgt)")),
            ("image", re.compile(".+(jpg|gif|png|svg)")),
            ("font", re.compile(".+(ttf|oft|woff2?)")),
            ("other", re.compile(".")),
        ))
        self.locs.ensure("src", task=name)

    def subtask_detail(self, task, fpath=None):
        targets = list(map(lambda x: fpath / x, self.content_mapping.keys()))
        task.update({
            "targets" : targets,
            'actions' : [
                (self.mkdirs, targets),
                self.move_files,
            ],
        })

        return task

    def move_files(self, targets):
        """
        Move all files into designated directories
        """
        root = pl.Path(targets[0]).parent
        assert(root.parent == self.locs.src)
        for poss in root.glob("**/*"):
            if poss.name in ["titlepage.xhtml", self.marker_file]:
                continue
            if poss.is_dir():
                continue
            if poss.parent.name in self.content_mapping.keys():
                continue
            if poss.name == "content.opf":
                poss.rename(root / poss.name)

            for content_type, regex in self.content_mapping.items():
                if regex.match(poss.suffix):
                    poss.rename(root / content_type / poss.name)
                    moved = True
                    break

class EbookSplitTask(dir_walker.DootDirWalker):
    """
    (GlobDirs: [data] -> build) split any epubs found in the project data
    """

    def __init__(self, name="epub::split", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data] , exts=[".epub"], rec=rec)
        self.locs.ensure("build", task=name)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.build / fpath.stem],
            "file_dep" : [ fpath ],
            "actions"  : [ self.make_cmd(self.action_convert), ],
        })
        return task

    def is_current(self, task:DootTask):
        return pl.Path(task.targets[0]).exists()

    def action_convert(self, dependencies, targets):
        return ["ebook-convert", dependencies[0], targets[0]]

class EbookNewTask(job.DootJob):
    """
    (-> [src]) Create a new stub structure for an ebook

    """

    def __init__(self, name="epub::new", locs:DootLocData=None):
        super().__init__(name, locs)
        self.marker_file = ".epub"
        self.paths : list[pl.Path|str] = [
            "content", "style", "image", "font", "image"
        ]
        self.files : list[pl.Path|str] = [
            "images/title.jpg"
        ]
        self.locs.ensure("src", task=name)

    def is_current(self, task):
        name = task.options['name']
        return (self.locs.src / name / self.marker_file).exists()

    def set_params(self):
        return [
            { "name" : "name", "short" : "n", "type": str, "default" : "default" }
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [ self.make_dirs,
                          self.make_titlepage,
                          self.make_default_styles
                         ],
            })
        return task

    def make_dirs(self, name):
        for sub_path in self.paths:
            targ = self.locs.src / name / sub_path
            if targ.exists():
                continue

            targ.mkdir(parents=True)

        (self.locs.src / name / self.marker_file).touch()

    def make_titlepage(self, name):
        tp = self.locs.src / name / "titlepage.xhtml"
        tp.write_text(title_template.read_text())

    def make_default_styles(self, name):
        style_base     = self.locs.src / name / "style"

        default_styles = style_base / "stylesheet.css"
        page_styles    = style_base / "page_styles.css"

        default_styles.write_text(css_template.read_text())
        page_styles.write_text(page_style_template.read_text())

class TODOEbookNewPandoc(EbookGlobberBase):
    """
    Build an ebook using pandoc
    """

    def __init__(self, name="epub::pandoc", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots=roots or [locs.src], rec=rec)
        self.locs.ensure("build", task=name)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [ self.make_cmd(self.build_ebook, fpath) ],
            "targets" : [ self.locs.build / f"{fpath.stem}.epub" ],
        })
        return task

    def build_epub(self, fpath, targets):
        cmd = [ "pandoc", "-o", targets[0] ]

        cmd += self.glob_files(fpath, rec=True)
        return cmd
