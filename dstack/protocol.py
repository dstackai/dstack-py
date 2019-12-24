from abc import ABC
from typing import Dict
from urllib import request, parse
import json


class Protocol(ABC):
    def send(self, endpoint: str, data: Dict) -> Dict:
        pass


class JsonProtocol(Protocol):
    ENCODING = "utf-8"

    def __init__(self, url: str):
        self.url = url

    def send(self, endpoint: str, data: Dict) -> Dict:
        req = request.Request(self.url + endpoint)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        data_bytes = json.dumps(data).encode('utf-8')  # needs to be bytes
        req.add_header("Content-Length", str(len(data_bytes)))
        response = request.urlopen(req, data_bytes)
        return json.loads(response.read(), encoding=self.ENCODING)
