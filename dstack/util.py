import typing as ty
from pathlib import Path
from uuid import uuid4
from os import path, makedirs
from functools import wraps
from hashlib import md5
import pickle
import json

HOME_APP_DIR = path.join(Path.home(), '.dstack')
makedirs(HOME_APP_DIR, exist_ok=True)
HOME_CACHE_DIR = path.join(HOME_APP_DIR, 'cache')
makedirs(HOME_CACHE_DIR, exist_ok=True)


def prepare_for_hash(*args, **kwargs) -> str:
    if len(kwargs) > 0 or len(args) > 0:
        return str(args) + json.dumps(kwargs, sort_keys=True)
    else:
        return '0'


def get_filename(s: str) -> str:
    m = md5()
    m.update(s.encode('utf-8'))
    return m.hexdigest()


def flash_cache(hash_func=prepare_for_hash, cache_dir=HOME_CACHE_DIR):

    def decorator(func):
        # func.__hash_func__ = hash_func

        @wraps(func)
        def wrapper(*args, **kwargs):

            filename = get_filename(hash_func(*args, **kwargs))
            full_path_to_file = path.join(cache_dir, filename)

            try:
                with open(full_path_to_file, 'rb') as f:
                    file = pickle.load(f)
                return file

            except (IOError, OSError, pickle.PickleError):
                rv = func(*args, **kwargs)
                with open(full_path_to_file, 'wb') as f:
                    pickle.dump(rv, f)
                return rv

        wrapper.__decorated__ = func

        return wrapper

    return decorator


def create_filename(tmp_dir: ty.Union[str, Path]) -> str:
    return str(create_path(tmp_dir))


def create_path(tmp_dir: ty.Union[str, Path]) -> Path:
    return tmp_dir / Path(str(uuid4()))


def is_jupyter() -> bool:
    return hasattr(globals(), "_dh")
