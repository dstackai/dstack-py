import inspect
import sys
import typing as ty
from functools import wraps
from pathlib import Path

import dstack.application.dependencies as dp


class Application:
    def __init__(self, function, **kwargs):
        self.controls = {k: v for k, v in kwargs.items() if k not in ["requirements", "depends", "project"]}
        self.kwargs = {k: v for k, v in kwargs.items() if k in ["requirements", "depends", "project"]}
        self.function = self.decorator(function)

    def dep(self) -> ty.List[dp.Dependency]:
        result = []

        requirements = self.kwargs.get("requirements")
        if requirements:
            result.append(dp.RequirementsDependency(Path(requirements)))

        project = self.kwargs.get("project")
        if project:
            result.append(dp.ProjectDependency())

        depends = self.kwargs.get("depends")
        if depends:
            for d in depends:
                if inspect.ismodule(d):
                    result.append(dp.ModuleDependency(d))
                else:
                    result.append(dp.PackageDependency(d))

        return result

    def decorator(self, func):
        if hasattr(func, "__decorated__"):
            func = func.__decorated__

        if hasattr(func, "__depends__"):
            func.__depends__ += self.dep()
        else:
            func.__depends__ = self.dep()

        if func.__module__ != "__main__":
            module = sys.modules[func.__module__]
            func.__depends__.append(dp.ModuleDependency(module))

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__decorated__ = func

        return wrapper
