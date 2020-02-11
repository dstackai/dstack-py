import base64
import io
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import uuid4

from dstack.config import from_yaml_file, Config
from dstack.protocol import Protocol, JsonProtocol


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class FrameData:
    def __init__(self, data: io.BytesIO,
                 description: Optional[str],
                 params: Optional[Dict],
                 settings: Optional[Dict] = None):
        self.data = str(base64.b64encode(data.getvalue()))[2:-1]
        self.description = description
        self.params = params
        self.settings = settings


class Handler(ABC):
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg"
    PLOTLY = "plotly"
    BOKEH = "bokeh"

    @abstractmethod
    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        pass

    @abstractmethod
    def media_type(self) -> str:
        pass


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
                 token: str,
                 handler: Handler,
                 auto_push: bool,
                 protocol: Protocol,
                 encryption: EncryptionMethod):
        self.stack = stack
        self.token = token
        self.auto_push = auto_push
        self.protocol = protocol
        self.encryption_method = encryption
        self.id = uuid4().__str__()
        self.index = 0
        self.handler = handler
        self.timestamp = time.time_ns()
        self.data: List[FrameData] = []

    def commit(self, obj, description: Optional[str] = None, params: Optional[Dict] = None):
        data = self.handler.as_frame(obj, description, params)
        encrypted_data = self.encryption_method.encrypt(data)
        self.data.append(encrypted_data)
        if self.auto_push:
            self.push_data(encrypted_data)

    def push(self) -> str:
        frame = self.new_frame()
        if not self.auto_push:
            frame["attachments"] = [filter_none(x.__dict__) for x in self.data]
            return self.send_push(frame)
        else:
            frame["total"] = self.index
            return self.send_push(frame)

    def push_data(self, data: FrameData):
        frame = self.new_frame()
        frame["index"] = self.index
        frame["attachments"][0] = filter_none(data.__dict__)
        self.index += 1
        self.send_push(frame)

    def new_frame(self) -> Dict:
        data = {"stack": self.stack,
                "token": self.token,
                "id": self.id,
                "timestamp": self.timestamp,
                "type": self.handler.media_type()}

        if not isinstance(self.encryption_method, NoEncryption):
            data["encryption"] = self.encryption_method.info()

        return data

    def send_access(self):
        req = {"stack": self.stack, "token": self.token}
        self.protocol.send("/stacks/access", req)

    def send_push(self, frame: Dict) -> str:
        res = self.protocol.send("/stacks/push", frame)
        return res["url"]


def filter_none(d):
    if isinstance(d, Dict):
        return {k: filter_none(v) for k, v in d.items() if v is not None}
    return d


def create_frame(stack: str,
                 handler: Handler,
                 profile: str = "default",
                 auto_push: bool = False,
                 protocol: Protocol = JsonProtocol("https://api.dstack.ai"),
                 config: Optional[Config] = None,
                 encryption: EncryptionMethod = NoEncryption()) -> StackFrame:
    if config is None:
        config = from_yaml_file()
    frame = StackFrame(stack, config.get_profile(profile).token, handler, auto_push, protocol, encryption)
    frame.send_access()
    return frame
