import copy
import inspect
import re
import shutil
import typing as ty
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4
import json

import cloudpickle

from textwrap import dedent

import dstack.util as util
from dstack.application import Application
from dstack.handler import EncoderFactory, DecoderFactory, Encoder, FrameData, Decoder
from dstack.application.controls import Control, Controller, TextField, View, TextFieldView, unpack_view
from dstack.application.dependencies import Dependency, ModuleDependency
from dstack.application.validators import int_validator, float_validator
from dstack.content import FileContent, MediaType

from typing import Any


class AppEncoderFactory(EncoderFactory):
    def accept(self, obj: Any) -> bool:
        return self.is_type(obj, "dstack.application.Application")

    def create(self) -> Encoder[Any]:
        return AppEncoder()


class AppDecoderFactory(DecoderFactory):
    def accept(self, obj: MediaType) -> bool:
        return self.is_media(obj.application, ["application/python"])

    def create(self) -> Decoder:
        return AppDecoder()


class AppEncoder(Encoder[Application]):
    def __init__(self, temp_dir: ty.Optional[str] = None, archive: str = "zip",
                 force_serialization: bool = False, _strict_type_check: bool = True):
        super().__init__()
        self._temp_dir = Path(temp_dir or gettempdir())
        self._archive = archive
        self._force_serialization = force_serialization
        self._strict_type_check = _strict_type_check
        self._copy_controls = True

    def encode(self, app, description: ty.Optional[str], params: ty.Optional[ty.Dict]) -> FrameData:
        force_serialization = self._force_serialization

        call_stack_frame = inspect.currentframe().f_back

        while call_stack_frame:
            module = inspect.getmodule(call_stack_frame)
            # Some options we must take into account here:
            # 1) module can be None if we are in Jupyter notebook
            # 2) if obj is defined in the Jupyter notebook obj.__module__ will be equal to "__main__"
            # 3) if push/encode is called from the module where obj is defined we must serialize
            if not module:
                force_serialization = (app.function.__module__ == "__main__")
                break
            elif module.__name__ == app.function.__module__:
                force_serialization = True

            call_stack_frame = call_stack_frame.f_back

        if force_serialization:
            deps = []
            for d in _get_deps(app.function):
                if not (isinstance(d, ModuleDependency) and d.module.__name__ == app.function.__module__):
                    deps.append(d)
        else:
            deps = _get_deps(app.function)

        controls = []

        # do some signature analysis here
        sig = inspect.signature(app.function)
        keys = list(app.controls.keys())
        for p in sig.parameters.values():
            if p.name in keys:
                if sig.parameters[p.name].annotation != inspect.Parameter.empty:
                    (is_optional, tpe) = _split_type(str(p.annotation))
                    value = app.controls[p.name]

                    if isinstance(value, Control):
                        if self._copy_controls:
                            value = copy.copy(value)

                        self._check_optional(is_optional, p.name, value)

                    if isinstance(value, TextField):
                        # TODO: Implement validation
                        # self._check_type(p.name, tpe, value)

                        controls.append(value)
            else:
                raise ValueError(f"Control '{p.name}' is not bound")

        controller = Controller(controls)

        stage_dir = util.create_path(self._temp_dir)

        _stage_deps(deps, stage_dir)

        _serialize(controller, stage_dir / "controller.pickle")

        if force_serialization:
            func_filename = "function.pickle"
            _serialize(_undress(app.function), stage_dir / func_filename)
            function_settings = {
                "type": "pickle",
                "data": func_filename
            }
            if app.function.__module__ != "__main__":
                fake_module_path = stage_dir / f"{app.function.__module__}.py"
                fake_module_path.write_text("")
        else:
            function_settings = {
                "type": "source",
                "data": f"{app.function.__module__}.{app.function.__name__}"
            }

        archived = util.create_filename(self._temp_dir)
        filename = shutil.make_archive(archived, self._archive, stage_dir)

        settings = {"cloudpickle": cloudpickle.__version__,
                    "archive": self._archive,
                    "function": function_settings}

        return FrameData(FileContent(Path(filename)),
                         MediaType("application/octet-stream", "application/python"),
                         description, params, settings)

    def _check_type(self, name: str, tpe: str, value: TextField):
        validator = value.validator
        if validator is None:
            if tpe == "int":
                value.validator = int_validator()
            elif tpe == "float":
                value.validator = float_validator()
        elif (tpe == "float" and validator.type() not in ["int", "float"]) \
                or tpe != validator.type():
            if self._strict_type_check:
                raise ValueError(f"Type of '{name}' is not matched to the control's validator: "
                                 f"required {tpe} but found {validator.type()}")

    def _check_optional(self, is_optional: bool, name, value: Control):
        if value.optional is None:
            value.optional = is_optional
        else:
            # if param in the function is optional, and the control is not but not vice versa
            if is_optional < value.optional:
                if self._strict_type_check:
                    raise ValueError(f"Parameter '{name}' is not optional but the control {value} is")


def _serialize(obj: ty.Any, path: Path):
    with path.open(mode="wb") as f:
        cloudpickle.dump(obj, f)


def _split_type(tpe: str) -> (bool, ty.Optional[str]):
    result = re.search(r"typing.Union\[(.+), NoneType]", tpe)
    return (True, result.group(1)) if result else (False, _type(tpe))


def _type(tpe: str) -> str:
    result = re.search(r"<class '(.+)'", tpe)
    return result.group(1) if result else tpe


def _get_deps(func: ty.Callable) -> ty.List[Dependency]:
    return func.__depends__ if hasattr(func, "__depends__") else []


def _undress(func: ty.Callable) -> ty.Callable:
    return func.__decorated__ if hasattr(func, "__decorated__") else func


def _stage_deps(deps: ty.List[Dependency], root: Path):
    # Function stages dependencies in one place on disk
    # root
    # |- project
    #       |- package1
    #           |- package1.1
    #               |- module1.py
    #               |- ...
    #           |- package1.2
    #           |- ...
    #       |- package2
    #       |- ...
    # |- wheels
    #       |- my_wheel_package1.whl
    #       |- my_wheel_package2.whl
    # |- requirements.txt

    deps = _clear_deps(deps)
    for dep in deps:
        for source in dep.collect():
            source.stage(root)

    # if dependency list is empty we need to make the directory anyway
    if len(deps) == 0:
        root.mkdir(parents=True)


def _clear_deps(deps: ty.List[Dependency]) -> ty.List[Dependency]:
    # Remove modules if project dependency exists
    # Deduplicate package deps
    return deps


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


class Execution:
    # TODO: Handle outputs
    def __init__(self, id: str, status: str, views: ty.List[View], output: ty.Optional[str]):
        self.output = output
        self.views = views
        self.status = status
        self.id = id


class AppExecutor:
    def __init__(self, app_dir):
        self.app_dir = app_dir

    def views(self, views: ty.Optional[ty.List[View]] = None) -> ty.List[View]:
        import subprocess
        import sys

        execution_id = str(uuid4())

        self._write_views(execution_id, views)

        p = subprocess.Popen([sys.executable, "execute_script.py", execution_id, 'False'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             cwd=self.app_dir
                             )
        p.wait()
        return self.poll(execution_id).views

    def execute(self, views: ty.Optional[ty.List[View]]) -> str:
        import subprocess
        import sys

        execution_id = str(uuid4())

        self._write_views(execution_id, views)

        subprocess.Popen([sys.executable, "execute_script.py", execution_id, 'True'],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         cwd=self.app_dir
                         )
        return execution_id

    def _write_views(self, execution_id, views):
        if views:
            execution = {
                'status': 'ready',
                'views': [v.pack() for v in views]
            }

            executions = Path(self.app_dir) / "executions"
            executions.mkdir(exist_ok=True)
            execution_file = executions / (execution_id + '.json')
            execution_file.write_text(json.dumps(execution))

    # def poll(self, execution_id: str) -> ty.Union[str, (ty.List[View], ty.Optional[Any])]:
    def poll(self, execution_id: str) -> ty.Optional[Execution]:
        execution_file = Path(self.app_dir) / "executions" / (execution_id + '.json')
        if execution_file.exists():
            execution = json.loads(execution_file.read_bytes())
            return Execution(execution_id, execution["status"],
                             [unpack_view(v) for v in execution["views"]],
                             execution.get("output"))
        else:
            return None


class AppDecoder(Decoder[AppExecutor]):
    def __init__(self):
        super().__init__()

    def decode(self, data: FrameData) -> AppExecutor:
        app_dir = _save_data(data)

        execution_base_script = """
import cloudpickle
import sys
import json
from pathlib import Path
from dstack.application.controls import unpack_view

execution_id = sys.argv[1]
apply = sys.argv[2] == 'True'

with open("controller.pickle", "rb") as f:
    controller = cloudpickle.load(f)

for c in controller.map.values():
    for i in range(len(c._parents)):
        c._parents[i] = controller.map[c._parents[i]._id]

executions = Path("executions")
executions.mkdir(exist_ok=True)
execution_file = executions / (execution_id + '.json')

if execution_file.exists():
    execution = json.loads(execution_file.read_bytes())
    views = controller.list([unpack_view(v) for v in execution["views"]])
else:
    views = controller.list()

execution = {
    'status': 'running' if apply else 'ready',
    'views': [v.pack() for v in views]
}

execution_file.write_text(json.dumps(execution))
"""

        function_settings = data.settings["function"]

        if function_settings["type"] == "source":
            def get_module_and_func(full_name):
                path = full_name.split(".")
                return ".".join(path[0:-1]), path[-1]

            func_module, func_name = get_module_and_func(function_settings["data"])

            execute_script = f"""
{execution_base_script}

from {func_module} import {func_name} as _func

if (apply):
    output = controller.apply(_func, views)
    # TODO: Handle failure
    execution['status'] = 'finished'
    execution['output'] = str(output)
    execution_file.write_text(json.dumps(execution))
"""
        else:
            execute_script = f"""
{execution_base_script}

with open("function.pickle", "rb") as f:
    func = cloudpickle.load(f)

if (apply):
    output = controller.apply(func, views)
    # TODO: Handle failure
    execution['status'] = 'finished'
    execution['output'] = str(output)
    execution_file.write_text(json.dumps(execution))
"""
        function_execute_file = Path(app_dir) / "execute_script.py"
        function_execute_file.write_text(dedent(execute_script).lstrip())

        return AppExecutor(app_dir)