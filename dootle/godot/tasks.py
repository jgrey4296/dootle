##-- imports
from __future__ import annotations

from functools import partial
import pathlib as pl
import shutil
##-- end imports

from doot.task import globber
from doot.task.tasker import DootTasker

# https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html

def task_godot_version():
    return { "basename"  : "godot::version",
             "actions"   : [
                 ActionsMixin.force(None, ["godot", "--version"]),
             ],
             "verbosity" : 2,
            }

def task_godot_test():
    """
    TODO run godot tests
    """
    return { "basename": "godot::test",
             "actions": []
            }

class GodotRunScene(globber.DootEagerGlobber):
    """
    ([root]) Globber to allow easy running of scenes
    """

    def __init__(self, name="godot::run:scene", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [dir.root], exts=[".tscn"], rec=rec)

    def set_params(self):
        return [
            { "name"    : "target", "short"   : "t", "type"    : str, "default" : "",},
            { "name"    : "debug", "short"   : "d", "type"    : bool, "default" : False,},
        ]

    def task_detail(self, task:dict):
        task.update({
            "actions" : [ self.make_cmd(self.run_scene_with_arg) ],
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [fpath],
        })
        task['actions'] += [ self.make_cmd(self.run_scene) ]
        return task

    def run_scene(self, dependencies):
        return self.run_scene_with_arg(dependencies[0], self.args['debug'])

    def run_scene_with_arg(self):
        args = ["godot"]
        if self.args['debug']:
            args.append("-d")

        args.append(self.args['target'])
        return args

class GodotRunScript(globber.EagerFileGlobber):
    """
    ([root]) Run a godot script, with debugging or without
    """

    def __init__(self, name="godot::run", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.root], exts=[".gd"], rec=rec)

    def filter(self, fpath):
        # TODO test script for implementing runnable interface
        return fpath.is_file()

    def set_params(self):
        return [
            { "name"    : "target", "short"   : "t", "type"    : str, "default" : "",},
            { "name"    : "debug", "short"   : "d", "type"    : bool, "default" : False,},
        ]

    def subtask_detail(self, task, fpath=None):
        task.update({ "verbosity" : 2,})
        task['actions'] += [
            self.make_cmd(self.run_cmd, [fpath]),
            self.regain_focus()
        ]

        return task

    def run_cmd(self, fpath):
        args = ["godot"]
        if self.args['debug']:
            args.append("-d")

        args.append("--no-window")
        args.append("--script")
        args.append(fpath)

        return args

class GodotBuild(DootTasker):
    """
    (-> [build]) build a godot project
    """

    def __init__(self, name="godot::build", locs:DootLocData=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            { "name" : "build_target", "short" : "t",    "type" : str, "default" : "osx",    "choices" : [("Mac OSX", ""), ("Android", ""),],},
            { "name" : "build_type",   "long"  : "type", "type" : str, "default" : "export", "choices" : [ ("export", ""), ("export-debug", "")]},
        ]

    def setup_detail(self, task):
        task.update({
            "actions" : [ "echo TODO build template export_presets.cfg"],
            "targets" : ["export_presets.cfg"],
        })
        return task

    def task_detail(self, task):
        return {
            "actions"  : [ self.make_cmd(self.cmd_builder) ],
            "targets"  : [ self.locs.build / "build.dmg" ],
            "file_dep" : [ "export_presets.cfg" ],
            "clean"    : True,
        }

    def cmd_builder(self, targets):
        return ["godot",
                "--no-window",
                f"--{self.args['build_type']}",
                self.args['build_target'],
                targets[0]
                ]

class GodotNewScene(DootTasker):
    """
    (-> [scenes])
    """

    def __init__(self, name="godot::new.scene", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("scenes", task=name)

    def set_params(self):
        return [
            { "name" : "name", "short" : "n", "type" : str, "default" : "default"},
        ]

    def task_detail(self, task):
        scene_file = self.locs.scenes / f"{self.args['name']}.tscn"
        task.update({
        "actions" : [
            lambda: scene_file.write_text("# Stub"),
            ],
            "targets" : [scene_file],
        })
        return task

class GodotCheckTask(globber.DootEagerGlobber):
    """
    ([root]) Lint all gd scripts in the project
    """

    def __init__(self, name="godot::check", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.root], exts=[".gd"], rec=rec)
        self.failures = set()
        self.locs.ensure("build", task=name)

    def set_params(self):
        return self.target_params()

    def setup_detail(self, task):
        task.update({
            "actions"  : [self.reset_failures],
            "teardown" : [self.report_failures],
            "target"   : [self.locs.build / "check_fails.report"]
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions"  : [
                self.make_force(self.build_check, fpath, handler=partial(self.handle_failure, fpath)),
            ],
            "file_dep" : [ fpath ],
            "uptodate" : [ False ],
        })
        return task

    def build_check(self, fpath):
        return ["godot", "--no-window", "--check-only", "--script", fpath]

    def handle_failure(self, fpath, result):
        print("Errors Found in: ", fpath)
        self.failures.add(fpath)
        return None

    def report_failures(self, targets):
        if not bool(self.failures):
            return

        report = ["==========",
                  "Failures Reported In:",
                  ]
        report += [f"- {fail}" for fail in self.failures]
        report += ["=========="]
        print("\n".join(report))
        self.write_to(targets[0], report)
        return False

    def reset_failures(self):
        self.failures = set()
