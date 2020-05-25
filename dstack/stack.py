import re
import time
from abc import ABC, abstractmethod
from platform import uname
from typing import Dict, List, Optional
from uuid import uuid4

from dstack import AutoHandler
from dstack.handler import FrameData, Handler
from dstack.protocol import Protocol
from dstack.version import __version__


class EncryptionMethod(ABC):
    @abstractmethod
    def encrypt(self, frame: FrameData) -> FrameData:
        pass

    @abstractmethod
    def info(self) -> Dict:
        pass


class NoEncryption(EncryptionMethod):
    def encrypt(self, frame: FrameData) -> FrameData:
        return frame

    def info(self) -> Dict:
        return {}


class StackFrame(object):
    def __init__(self,
                 stack: str,
                 user: str,
                 token: str,
                 auto_push: bool,
                 protocol: Protocol,
                 encryption: EncryptionMethod):
        self.stack = stack
        self.user = user
        self.token = token
        self.auto_push = auto_push
        self.protocol = protocol
        self.encryption_method = encryption
        self.id = uuid4().__str__()
        self.index = 0
        self.timestamp = int(round(time.time() * 1000))  # milliseconds
        self.data: List[FrameData] = []

    def commit(self, obj,
               description: Optional[str] = None,
               params: Optional[Dict] = None,
               handler: Handler = AutoHandler(), **kwargs):
        """Add data to the stack frame.

        Args:
            obj: A data to commit. Data will be preprocessed by the handler but dependently on auto_push
                mode will be sent to server or not. If auto_push is False then the data won't be sent.
                Explicit push call need anyway to process committed data. auto_push is useful only in the
                case of multiple data objects in the stack frame, e.g. set of plots with settings.
            description: Description of the data.
            params: Parameters associated with this data, e.g. plot settings.
            handler: Handler to use, by default it is AutoHandler.
            **kwargs: Optional parameters is an alternative to params. If both are present this one will
                be merged into params.
        """
        params = merge_or_none(params, kwargs)
        data = handler.encode(obj, description, params)
        encrypted_data = self.encryption_method.encrypt(data)
        self.data.append(encrypted_data)
        if self.auto_push:
            self.push_data(encrypted_data)

    def push(self, message: Optional[str] = None) -> str:
        """Push all commits to server. In the case of auto_push mode it sends only a total number
        of elements in the frame. So call this method is obligatory to close frame anyway.

        Args:
            message: Push message to describe what's new in this revision.
        Returns:
            Stack URL.
        """
        frame = self.new_frame()
        if message:
            frame["message"] = message

        if not self.auto_push:
            frame["attachments"] = [filter_none(x.__dict__) for x in self.data]
            return self.send_push(frame)
        else:
            frame["size"] = self.index
            return self.send_push(frame)

    def push_data(self, data: FrameData):
        frame = self.new_frame()
        frame["index"] = self.index
        frame["attachments"] = [filter_none(data.__dict__)]
        self.index += 1
        self.send_push(frame)

    def new_frame(self) -> Dict:
        data = {"id": self.id,
                "timestamp": self.timestamp,
                "client": "dstack-py",
                "version": __version__,
                "os": get_os_info()}

        if not isinstance(self.encryption_method, NoEncryption):
            data["encryption"] = self.encryption_method.info()

        return data

    def send_access(self):
        self.protocol.access(self.stack_path(), self.token)

    def send_push(self, frame: Dict) -> str:
        res = self.protocol.push(self.stack_path(), self.token, frame)
        return res["url"]

    def stack_path(self) -> str:
        return stack_path(self.user, self.stack)


def filter_none(d):
    if isinstance(d, Dict):
        return {k: filter_none(v) for k, v in d.items() if v is not None}
    return d


def get_os_info() -> Dict:
    info = uname()
    return {"sysname": info[0], "release": info[2], "version": info[3], "machine": info[4]}


def stack_path(user: str, stack: str) -> str:
    if re.match("^[a-zA-Z0-9-_/]{3,255}$", stack):
        return stack[1:] if stack[0] == "/" else f"{user}/{stack}"
    else:
        raise ValueError("Stack name can contain only latin letters, digits, slash and underscore")


def merge_or_none(x: Optional[Dict], y: Optional[Dict]) -> Optional[Dict]:
    x = {} if x is None else x.copy()
    x.update(y)
    return None if len(x) == 0 else x
