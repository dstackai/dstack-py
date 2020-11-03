import inspect
import shutil
import typing as ty
from pathlib import Path
from tempfile import gettempdir

import cloudpickle

import dstack.util as util
from dstack import Encoder, FrameData, DecoratedValue
from dstack.app.controls import Control, Controller
from dstack.app.dependencies import Dependency, ModuleDependency
from dstack.content import FileContent, MediaType


class ControlWrapper(DecoratedValue):
    def __init__(self, control: Control):
        self.control = control

    def decorate(self) -> ty.Dict[str, ty.Any]:
        return {"type": "control", "class": self.control.__class__.__name__}


class AppEncoder(Encoder[ty.Callable]):
    def __init__(self, temp_dir: ty.Optional[str] = None, archive: str = "zip", force_serialization: bool = False):
        super().__init__()
        self._temp_dir = Path(temp_dir or gettempdir())
        self._archive = archive
        self._force_serialization = force_serialization

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

        _check_signature(obj, list(params.keys()))

        stage_dir = util.create_path(self._temp_dir)

        _stage_deps(deps, stage_dir)

        controls = []

        for k in params.keys():
            value = params[k]
            if isinstance(value, Control):
                controls.append(value)
                params[k] = ControlWrapper(value)

        controller = Controller(controls)

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


def _serialize(obj: ty.Any, path: Path):
    with path.open(mode="wb") as f:
        cloudpickle.dump(obj, f)


def _check_signature(func: ty.Callable, keys: ty.List[str]):
    sig = inspect.signature(func)
    for p in sig.parameters.values():
        if not (p.name in keys):
            raise ValueError(f"Parameter '{p.name}' is not bound")


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


def _clear_deps(deps: ty.List[Dependency]) -> ty.List[Dependency]:
    # Remove modules if project dependency exists
    # Deduplicate package deps
    return deps
