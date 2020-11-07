import os
import shutil
import subprocess
import sys
import typing as ty
from pathlib import Path
from tempfile import gettempdir
from textwrap import dedent
from unittest import TestCase

import dstack.app.controls as ctrl
import dstack.app.dependencies as dp
import dstack.util as util
from dstack.app import depends
from dstack.app.handlers import AppEncoder
from dstack.app.validators import int_validator
from dstack.handler import FrameData
from dstack.version import __version__ as dstack_version
from tests.app.test_package.mymodule import test_app, foo


class TestApp(TestCase):
    class Env(object):
        def __init__(self, path: Path):
            self.path = path

            if path.exists():
                shutil.rmtree(str(path))

            subprocess.run([sys.executable, "-m", "venv", str(path)])

        def dispose(self):
            shutil.rmtree(str(self.path))

        def run_script(self, cmd: ty.List[str], working_directory: Path) -> str:
            os.chdir(working_directory)
            python = self.path / "bin" / "python"
            result = subprocess.run([str(python)] + cmd, cwd=working_directory, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.stdout.decode()

        def pip_install(self, path: Path):
            pip = self.path / "bin" / "pip"

            if path.suffix == ".whl":
                subprocess.run([str(pip), "install", str(path)])
            else:
                subprocess.run([str(pip), "install", "-r", str(path)])

        def install_dstack(self):
            wd = dp._working_directory()
            project_root = dp._find_project_root(wd)
            subprocess.run([sys.executable, "setup.py", "bdist_wheel"], cwd=project_root)
            wheel = project_root / "dist" / f"dstack-{dstack_version}-py3-none-any.whl"
            self.pip_install(wheel)

    def test_first_example(self):
        @ctrl.update
        def update(control, text_field):
            control.data = str(int(text_field.data) * 2)

        c1 = ctrl.TextField("10", id="c1", validator=int_validator())
        c2 = ctrl.TextField(id="c2", depends=c1, data=update, validator=int_validator())

        encoder = AppEncoder()
        frame_data = encoder.encode(test_app, None, params={
            "x": c1,
            "y": c2
        })

        function_settings = frame_data.settings["function"]
        self.assertEqual("source", function_settings["type"])
        self.assertEqual(test_app.__name__, function_settings["data"])

        base_dir = gettempdir() / Path("stage_simple")
        app_dir = self._save_data(frame_data, filename=base_dir / "app")

        env = self.Env(base_dir / "venv")
        env.install_dstack()
        env.pip_install(app_dir / "requirements.txt")

        test_script = f"""
        from tests.app.test_package.mymodule import test_app
        from inspect import signature
        
        # to be sure that all dependencies are installed
        import deprecation
        import yaml
        
        import cloudpickle
        # test_app(10, 11)

        with open("controller.pickle", "rb") as f:
            controller = cloudpickle.load(f)

        views = controller.list()
        controller.apply({function_settings["data"]}, views)
        """
        test_file = Path(app_dir) / "test_script.py"
        test_file.write_text(dedent(test_script).lstrip())
        output = env.run_script(["test_script.py"], app_dir)
        self.assertEqual("Here is bar!\nHere is foo!\nMy app: x=10 y=20\n", output)
        env.dispose()
        shutil.rmtree(base_dir)

    def test_jupyter_like_env(self):
        @ctrl.update
        def update(control, text_field):
            control.data = str(int(text_field.data) * 2)

        def baz():
            print("baz")

        @depends("tests.app.test_package")
        def my_func(x: int, y: int):
            foo()
            baz()
            return x + y

        c1 = ctrl.TextField("10", id="c1", validator=int_validator())
        c2 = ctrl.TextField(id="c2", depends=c1, data=update, validator=int_validator())
        encoder = AppEncoder(force_serialization=True)
        frame_data = encoder.encode(my_func, None, params={
            "x": c1,
            "y": c2
        })

        function_settings = frame_data.settings["function"]
        self.assertEqual("pickle", function_settings["type"])

        base_dir = gettempdir() / Path("stage_jupyter_like")
        app_dir = self._save_data(frame_data, filename=base_dir / "app")

        env = self.Env(base_dir / "venv")
        env.install_dstack()

        pickled_function_path = Path(app_dir) / function_settings["data"]
        self.assertTrue(pickled_function_path.exists())

        test_script = f"""
        from inspect import signature
        import cloudpickle
    
        with open("controller.pickle", "rb") as f:
            controller = cloudpickle.load(f)

        with open("{pickled_function_path.name}", "rb") as f:
            func = cloudpickle.load(f)
            
        views = controller.list()
        controller.apply(func, views)
        """
        test_file = Path(app_dir) / "test_script.py"
        test_file.write_text(dedent(test_script).lstrip())

        output = env.run_script(["test_script.py"], app_dir)
        self.assertEqual("Here is bar!\nHere is foo!\nbaz\n", output)
        env.dispose()

        shutil.rmtree(base_dir)

    def test_signature_analysis_for_optionals(self):
        def my_func1(x: int, y: int):
            return x + y

        def my_func2(x: int, y: ty.Optional[int]):
            return x + y

        c1 = ctrl.TextField("10", id="c1", validator=int_validator())
        c2 = ctrl.TextField("20", id="c2")

        encoder = AppEncoder(force_serialization=True)
        # to make visible controls changes outside after encoding
        # it's much easier compared with controller deserialization

        encoder._copy_controls = False

        encoder.encode(my_func1, None, params={
            "x": c1,
            "y": c2
        })
        #
        self.assertFalse(c1.optional)
        self.assertFalse(c2.optional)

        c1 = ctrl.TextField("10", id="c1", validator=int_validator())
        c2 = ctrl.TextField("20", id="c2")

        encoder.encode(my_func2, None, params={
            "x": c1,
            "y": c2
        })

        self.assertFalse(c1.optional)
        self.assertTrue(c2.optional)

        c1 = ctrl.TextField("10", id="c1", validator=int_validator(), optional=True)
        c2 = ctrl.TextField("20", id="c2")

        try:
            encoder.encode(my_func2, None, params={
                "x": c1,
                "y": c2
            })
            self.fail()
        except ValueError:
            pass

    @staticmethod
    def _save_data(data: FrameData, filename: ty.Optional[Path] = None, temp_dir: ty.Optional[str] = None) -> Path:
        temp_dir = temp_dir or gettempdir()
        filename = filename or util.create_path(temp_dir)

        path = Path(filename)

        if path.exists():
            shutil.rmtree(filename)

        path.mkdir(parents=True)

        archived = util.create_filename(temp_dir)

        with data.data.stream() as stream:
            with open(archived, "wb") as f:
                f.write(stream.read())

        archive = data.settings["archive"]
        shutil.unpack_archive(archived, extract_dir=str(filename), format=archive)

        return filename
