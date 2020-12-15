import typing as ty
from pathlib import Path
from uuid import uuid4
from os import path, makedirs

HOME_APP_DIR = path.join(Path.home(), '.dstack')
makedirs(HOME_APP_DIR, exist_ok=True)
HOME_CACHE_DIR = path.join(HOME_APP_DIR, 'cache')
makedirs(HOME_CACHE_DIR, exist_ok=True)


def create_filename(tmp_dir: ty.Union[str, Path]) -> str:
    return str(create_path(tmp_dir))


def create_path(tmp_dir: ty.Union[str, Path]) -> Path:
    return tmp_dir / Path(str(uuid4()))


def is_jupyter() -> bool:
    return hasattr(globals(), "_dh")
