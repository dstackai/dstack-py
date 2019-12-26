import base64
import io
import time
from typing import Dict, List, Optional
from uuid import uuid4
from abc import ABC

from dstack.protocol import Protocol, JsonProtocol


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class ServerException(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class AccessDeniedException(ServerException):
    ACCESS_DENIED_STATUS_CODE = 1

    def __init__(self, message: str):
        super(AccessDeniedException, self).__init__(self.ACCESS_DENIED_STATUS_CODE, message)


class FrameData:
    def __init__(self, data: io.BytesIO,
                 description: Optional[str],
                 params: Optional[Dict]):
        self.data = str(base64.b64encode(data.getvalue()))[2:-1]
        self.description = description
        self.params = params


class Handler(ABC):
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg"
    PLOTLY = "plotly"

    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        pass

    def media_type(self) -> str:
        pass


class EncryptionMethod(ABC):
    def encrypt(self, frame: FrameData) -> FrameData:
        pass

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

    def commit(self, obj, description: Optional[str], params: Optional[Dict] = None):
        data = self.handler.as_frame(obj, description, params)
        encrypted_data = self.encryption_method.encrypt(data)
        self.data.append(encrypted_data)
        if self.auto_push:
            self.push_data(encrypted_data)
        return

    def push(self):
        frame = self.new_frame()
        if not self.auto_push:
            frame["attachments"] = [filter_none(x.__dict__) for x in self.data]
            self.send_push(frame)
        else:
            frame["total"] = self.index
            self.send_push(frame)

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
        res = self.protocol.send("/stacks/access", req)
        if res["status"] != 0:
            raise AccessDeniedException(res["message"])

    def send_push(self, frame: Dict):
        res = self.protocol.send("/stacks/push", frame)
        if res["status"] != 0:
            raise ServerException(res["status"], res["message"])


def filter_none(d):
    if isinstance(d, Dict):
        return {k: filter_none(v) for k, v in d.items() if v is not None}
    return d


def create_frame(stack: str,
                 token: str,
                 handler: Handler,
                 auto_push: bool = False,
                 protocol: Protocol = JsonProtocol("https://api.dstack.ai"),
                 encryption: EncryptionMethod = NoEncryption()) -> StackFrame:
    frame = StackFrame(stack, token, handler, auto_push, protocol, encryption)
    frame.send_access()
    return frame
