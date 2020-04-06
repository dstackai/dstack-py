import base64
import json
from abc import ABC, abstractmethod
from typing import Dict
from urllib import request
from urllib.error import HTTPError


class ServerException(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class Protocol(ABC):
    @abstractmethod
    def send(self, endpoint: str, data: Dict) -> Dict:
        pass


class JsonProtocol(Protocol):
    ENCODING = "utf-8"
    MAX_SIZE = 5_000_000

    def __init__(self, url: str):
        self.url = url

    def send(self, endpoint: str, data: Dict) -> Dict:
        data_bytes = json.dumps(data).encode(self.ENCODING)
        size = len(data_bytes)
        token = data.pop("token")
        if size < self.MAX_SIZE:
            return self.do_request(endpoint, data_bytes, token)
        else:
            attachments = data["attachments"]
            content = []
            for index, attach in enumerate(attachments):
                content.append(base64.b64decode(attach.pop("data")))
                attach["length"] = len(content[index])
            data_bytes = json.dumps(data).encode(self.ENCODING)
            result = self.do_request(endpoint, data_bytes, token)
            for attach in result["attachments"]:
                self.do_upload(attach["upload_url"], content[attach["index"]])
            return result

    def do_request(self, endpoint: str, data_bytes: bytes, token: str) -> Dict:
        req = request.Request(self.url + endpoint)
        req.add_header("Content-Type", f"application/json; charset={self.ENCODING}")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Length", str(len(data_bytes)))
        try:
            response = request.urlopen(req, data_bytes)
            return json.loads(response.read(), encoding=self.ENCODING)
        except HTTPError as e:
            raise ServerException(e.code, e.reason)

    @staticmethod
    def do_upload(upload_url: str, data: bytes):
        req = request.Request(url=upload_url, data=data, method="PUT")
        return request.urlopen(req)
