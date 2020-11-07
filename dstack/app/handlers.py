import copy
import inspect
import re
import shutil
import typing as ty
from pathlib import Path
from tempfile import gettempdir

import cloudpickle

import dstack.util as util
from dstack import Encoder, FrameData, DecoratedValue
from dstack.app.controls import Control, Controller, TextField
from dstack.app.dependencies import Dependency, ModuleDependency
from dstack.app.validators import int_validator, float_validator
from dstack.content import FileContent, MediaType


class ControlWrapper(DecoratedValue):
    def __init__(self, control: Control):
        self.control = control

    def decorate(self) -> ty.Dict[str, ty.Any]:
        return {"type": "control", "class": self.control.__class__.__name__}


class AppEncoder(Encoder[ty.Callable]):
    def __init__(self, temp_dir: ty.Optional[str] = None, archive: str = "zip",
                 force_serialization: bool = False, _strict_type_check: bool = True):
        super().__init__()
        self._temp_dir = Path(temp_dir or gettempdir())
        self._archive = archive
        self._force_serialization = force_serialization
        self._strict_type_check = _strict_type_check
        self._copy_controls = True

    def encode(self, obj, description: ty.Optional[str], params: ty.Optional[ty.Dict]) -> FrameData:
        force_serialization = self._force_serialization

        call_stack_frame = inspect.currentframe().f_back

        while call_stack_frame:
            module = inspect.getmodule(call_stack_frame)
            if not module or module.__name__ == obj.__module__:
                force_serialization = True
            call_stack_frame = call_stack_frame.f_back

        if force_serialization:
            deps = []
            for d in _get_deps(obj):
                if not (isinstance(d, ModuleDependency) and d.module.__name__ == obj.__module__):
                    deps.append(d)
        else:
            deps = _get_deps(obj)

        controls = []

        # do some signature analysis here
        sig = inspect.signature(obj)
        keys = list(params.keys())
        for p in sig.parameters.values():
            if p.name in keys:
                if sig.parameters[p.name].annotation != inspect.Parameter.empty:
                    (is_optional, tpe) = _split_type(str(p.annotation))
                    value = params[p.name]

                    if isinstance(value, Control):
                        if self._copy_controls:
                            value = copy.copy(value)

                        self._check_optional(is_optional, p.name, value)

                    if isinstance(value, TextField):
                        self._check_type(p.name, tpe, value)

                        controls.append(value)
                        params[p.name] = ControlWrapper(value)
            else:
                raise ValueError(f"Parameter '{p.name}' is not bound")

        controller = Controller(controls)

        stage_dir = util.create_path(self._temp_dir)

        _stage_deps(deps, stage_dir)

        _serialize(controller, stage_dir / "controller.pickle")

        if force_serialization:
            func_filename = "function.pickle"
            _serialize(_undress(obj), stage_dir / func_filename)
            function_settings = {
                "type": "pickle",
                "data": func_filename
            }
            if obj.__module__ != "__main__":
                fake_module_path = stage_dir / f"{obj.__module__}.py"
                fake_module_path.write_text("")
        else:
            function_settings = {
                "type": "source",
                "data": obj.__qualname__
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
