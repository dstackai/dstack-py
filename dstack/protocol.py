from abc import ABC
from typing import Dict
from urllib import request, parse
import json


class Protocol(ABC):
    def send(self, data: Dict) -> Dict:
        pass


class JsonProtocol(Protocol):
    def __init__(self, url: str):
        self.url = url

    def send(self, data: Dict) -> Dict:
        data = parse.urlencode(data).encode(encoding="utf-8")
        req = request.Request(self.url, data=data)
        response = request.urlopen(req)
        return json.loads(response.read(), encoding="utf-8")
