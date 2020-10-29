from pathlib import Path
from typing import List, Callable

from dstack.app.dependencies import Dependency, RequirementsDependency, ProjectDependency, ModuleDependency, \
    PackageDependency


def depends(*args, **kwargs):
    def dep() -> List[Dependency]:
        result = []

        requirements = kwargs.get("requirements")
        if requirements:
            result.append(RequirementsDependency(Path(requirements)))

        project = kwargs.get("project")
        if project:
            result.append(ProjectDependency())

        for d in args:
            if inspect.ismodule(d):
                result.append(ModuleDependency(d))
            else:
                result.append(PackageDependency(d))

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
            func.__depends__.append(ModuleDependency(module))

        def wrapper(*args, **kwargs):
            func(args, kwargs)

        wrapper.__decorated__ = func

        return wrapper

    return decorator


def _get_deps(func: Callable) -> List[Dependency]:
    return func.__depends__ if hasattr(func, "__depends__") else []


def _undress(func: Callable) -> Callable:
    return func.__decorated__ if hasattr(func, "__decorated__") else func



