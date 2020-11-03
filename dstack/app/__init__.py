import inspect
import sys
import typing as ty
from functools import wraps
from pathlib import Path

import dstack.app.dependencies as dp


def depends(*args, **kwargs):
    def dep() -> ty.List[dp.Dependency]:
        result = []

        requirements = kwargs.get("requirements")
        if requirements:
            result.append(dp.RequirementsDependency(Path(requirements)))

        project = kwargs.get("project")
        if project:
            result.append(dp.ProjectDependency())

        for d in args:
            if inspect.ismodule(d):
                result.append(dp.ModuleDependency(d))
            else:
                result.append(dp.PackageDependency(d))

        return result

    def decorator(func):
        if hasattr(func, "__decorated__"):
            func = func.__decorated__

        if hasattr(func, "__depends__"):
            func.__depends__ += dep()
        else:
            func.__depends__ = dep()

        if func.__module__ != "__main__":
            module = sys.modules[func.__module__]
            func.__depends__.append(dp.ModuleDependency(module))

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__decorated__ = func

        return wrapper

    return decorator



