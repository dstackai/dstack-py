import base64
import io
import json
from typing import Dict, List
from uuid import uuid4

from dstack.version import Version


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class FrameData:
    def __init__(self, buf: io.BytesIO, description: str, params: Dict, media_type: str):
        self.buf = str(base64.b64encode(buf.getvalue()))[2:-1]
        self.description = description
        self.params = params
        self.media_type = media_type


class Handler:
    def accept(self, obj) -> bool:
        return False

    def as_frame(self, obj, description: str, params: Dict) -> FrameData:
        pass


class EncryptionMethod:
    def encrypt(self, frame: FrameData) -> FrameData:
        pass

    def name(self) -> str:
        pass

    def version(self) -> Version:
        pass


class NoEncryption(EncryptionMethod):
    def encrypt(self, frame: FrameData) -> FrameData:
        return frame

    def name(self) -> str:
        return "no_encryption"

    def version(self) -> Version:
        return Version(1, 0, 0)


class StackFrame(object):
    def __init__(self,
                 name: str,
                 user: str,
                 token: str,
                 auto_push: bool = False,
                 server: str = "api.dstack.ai",
                 encryption_method: EncryptionMethod = NoEncryption()):
        self.stack_name = name
        self.user = user
        self.token = token
        self.auto_push = auto_push
        self.server = server
        self.encryption_method = encryption_method
        self.id = uuid4().__str__()
        self.index = 0
        self.handlers: List[Handler] = []
        self.data: List[FrameData] = []
        pass

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
        return {"name": self.stack_name, "user": self.user, "token": self.token, "id": self.id, "data": []}

    def send(self, frame: Dict):
        print(json.dumps(frame, indent=2))
        # print(frame["data"][0])

    pass
