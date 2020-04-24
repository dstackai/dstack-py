import copy
import io
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from dstack.config import YamlConfig, get_config


class Logger(ABC):
    @abstractmethod
    def log(self, data: Dict):
        pass


class FileLogger(Logger):
    def __init__(self, filename: str):
        self.filename = filename

    def log(self, data: Dict):
        path = Path(self.filename)
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        with open(self.filename, "a") as f:
            print(json.dumps(data), file=f)


class InMemoryLogger(Logger):
    def __init__(self):
        self.io = io.StringIO()

    def log(self, data: Dict):
        print(json.dumps(data), file=self.io)


ERASE_BINARY_DATA = 1
ERASE_PARAM_VALUES = 2
ERASE_PARAM_NAMES = 4
ERASE_DESCRIPTION = 8
ERASE_PUSH_MESSAGE = 16
ERASE_STACK_NAME = 32

ERASE_ALL = ERASE_BINARY_DATA | ERASE_PARAM_VALUES | ERASE_PARAM_NAMES | \
            ERASE_DESCRIPTION | ERASE_PUSH_MESSAGE | ERASE_STACK_NAME

__erasure_flags: int = ERASE_BINARY_DATA | ERASE_PARAM_VALUES
__logger: Optional[Logger] = None


def debug(**kwargs) -> bool:
    if __logger:
        line = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        for key, value in kwargs.items():
            if key == "data":
                value = erase_sensitive_data(value, __erasure_flags)
            line[key] = value
        __logger.log(line)
        return True
    else:
        return False


def enable(erasure_flags: int = ERASE_BINARY_DATA | ERASE_PARAM_VALUES,
           logger: Optional[Logger] = None):
    def get_log_file() -> str:
        config = get_config()
        if isinstance(config, YamlConfig):
            return str(config.path.parent / "logs" / datetime.now().strftime("%Y-%m-%d.log"))
        else:
            raise ValueError("Can't create logger, please specify it explicitly")

    global __erasure_flags, __logger
    __erasure_flags = erasure_flags
    __logger = logger if logger else FileLogger(get_log_file())


def disable():
    global __logger
    __logger = None


def get_logger():
    return __logger


def erase_sensitive_data(data: Dict, flags: int) -> Dict:
    def erase(d: Dict, name: str):
        obj = d.get(name, None)

        if obj is None:
            return

        d[name] = f"erased type=str len={len(obj)}" if isinstance(obj, str) else f"erased type={type(obj)}"

    def erase_name(ind: int):
        return f"erased{ind}"

    result = copy.deepcopy(data)
    attachments = result["attachments"] if result and "attachments" in result else []

    for attach in attachments:
        if flags & ERASE_BINARY_DATA:
            erase(attach, "data")

        params = attach.get("params", None)

        if params:
            if flags & ERASE_PARAM_VALUES:
                for p in params.keys():
                    erase(params, p)

            if flags & ERASE_PARAM_NAMES:
                new_params = {}
                for index, p in enumerate(params.keys()):
                    new_params[erase_name(index)] = params[p]
                attach["params"] = new_params

            if flags & ERASE_DESCRIPTION:
                erase(attach, "description")

    if flags & ERASE_PUSH_MESSAGE:
        erase(result, "message")

    if flags & ERASE_STACK_NAME:
        erase(result, "stack")

    return result
