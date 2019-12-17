import base64
import io
import json
from typing import Dict, List
from uuid import uuid4
from abc import ABC


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class FrameData:
    def __init__(self, buf: io.BytesIO, description: str, params: Dict, media_type: str):
        self.buf = str(base64.b64encode(buf.getvalue()))[2:-1]
        self.description = description
        self.params = params
        self.media_type = media_type


class Handler(ABC):
    IMAGE_PNG = "image/png"

    def accept(self, obj) -> bool:
        pass

    def as_frame(self, obj, description: str, params: Dict) -> FrameData:
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
                 stack_name: str,
                 user: str,
                 token: str,
                 auto_push: bool = False,
                 server: str = "api.dstack.ai",
                 encryption: EncryptionMethod = NoEncryption()):
        self.stack_name = stack_name
        self.user = user
        self.token = token
        self.auto_push = auto_push
        self.server = server
        self.encryption_method = encryption
        self.id = uuid4().__str__()
        self.index = 0
        self.handlers: List[Handler] = []
        self.data: List[FrameData] = []

    def commit(self, obj, description: str, params: Dict):
        for handler in self.handlers:
            if handler.accept(obj):
                data = handler.as_frame(obj, description, params)
                encrypted_data = self.encryption_method.encrypt(data)
                self.data.append(encrypted_data)
                if self.auto_push:
                    self.push_data(encrypted_data)
                return
        raise UnsupportedObjectTypeException(obj)

    def push(self):
        if not self.auto_push:
            frame = self.create_frame()
            frame["data"] = [x.__dict__ for x in self.data]
            self.send(frame)

    def push_data(self, data: FrameData):
        frame = self.create_frame()
        frame["index"] = self.index
        frame["data"][0] = data.__dict__
        self.index += 1
        self.send(frame)

    def register(self, handler):
        self.handlers.append(handler)
        return self

    def create_frame(self) -> Dict:
        data = {"stack_name": self.stack_name,
                "user": self.user,
                "token": self.token,
                "id": self.id,
                "data": []}

        if self.encryption_method is not NoEncryption:
            data["encryption"] = self.encryption_method.info()

        return data

    def send(self, frame: Dict):
        print(json.dumps(frame, indent=2))
        # print(frame["data"][0])

    pass
