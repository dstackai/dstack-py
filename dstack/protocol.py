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

    def __init__(self, url: str):
        self.url = url

    def send(self, endpoint: str, data: Dict) -> Dict:
        print(self.url + endpoint)
        req = request.Request(self.url + endpoint)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", f"Bearer {data['token']}")
        del data["token"]
        data_bytes = json.dumps(data).encode('utf-8')
        req.add_header("Content-Length", str(len(data_bytes)))
        try:
            response = request.urlopen(req, data_bytes)
            return json.loads(response.read(), encoding=self.ENCODING)
        except HTTPError as e:
            raise ServerException(e.code, e.reason)
