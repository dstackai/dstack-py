import base64
import io
import time
from typing import Dict, List
from uuid import uuid4
from abc import ABC

from dstack.protocol import Protocol, JsonProtocol


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class FrameData:
    def __init__(self, buf: io.BytesIO, description: str, params: Dict):
        self.buf = str(base64.b64encode(buf.getvalue()))[2:-1]
        self.description = description
        self.params = params


class Handler(ABC):
    IMAGE_PNG = "image/png"

    def accept(self, obj) -> bool:
        pass

    def as_frame(self, obj, description: str, params: Dict) -> FrameData:
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
                 auto_push: bool = False,
                 protocol: Protocol = JsonProtocol("api.dstack.ai"),
                 encryption: EncryptionMethod = NoEncryption()):
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

    def commit(self, obj, description: str, params: Dict = {}):
        if self.handler.accept(obj):
            data = self.handler.as_frame(obj, description, params)
            encrypted_data = self.encryption_method.encrypt(data)
            self.data.append(encrypted_data)
            if self.auto_push:
                self.push_data(encrypted_data)
            return
        else:
            raise UnsupportedObjectTypeException(obj)

    def push(self):
        if not self.auto_push:
            frame = self.create_frame()
            frame["data"] = [x.__dict__ for x in self.data]
            self.send(frame)
        else:
            frame = self.create_frame()
            frame["total"] = self.index
            self.send(frame)

    def push_data(self, data: FrameData):
        frame = self.create_frame()
        frame["index"] = self.index
        frame["data"][0] = data.__dict__
        self.index += 1
        self.send(frame)

    def create_frame(self) -> Dict:
        data = {"stack": self.stack,
                "token": self.token,
                "id": self.id,
                "timestamp": self.timestamp,
                "type": self.handler.media_type()}

        if not isinstance(self.encryption_method, NoEncryption):
            data["encryption"] = self.encryption_method.info()

        return data

    def send(self, frame: Dict):
        self.protocol.send(frame)
        # print(json.dumps(frame, indent=2))
        # print(frame["data"][0])

    pass
