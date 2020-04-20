import base64
import json
import ssl
from abc import ABC, abstractmethod
from typing import Dict, Optional

import requests


class MatchException(ValueError):
    def __init__(self, params: Dict):
        self.params = params

    def __str__(self):
        return f"Can't match parameters {self.params}"


class Protocol(ABC):
    @abstractmethod
    def push(self, data: Dict, token: str) -> Dict:
        pass

    @abstractmethod
    def access(self, stack: str, token: str) -> Dict:
        pass

    @abstractmethod
    def pull(self, stack: str, token: Optional[str], params: Optional[Dict]) -> Dict:
        pass

    @abstractmethod
    def download(self, url, filename):
        pass


class JsonProtocol(Protocol):
    ENCODING = "utf-8"
    MAX_SIZE = 5_000_000

    def __init__(self, url: str, verify: bool):
        self.url = url
        self.verify = verify
        self.context = ssl._create_unverified_context() if not verify else None

    def push(self, data: Dict, token: str) -> Dict:
        data_bytes = json.dumps(data).encode(self.ENCODING)
        size = len(data_bytes)
        if size < self.MAX_SIZE:
            result = self.do_request("/stacks/push", data_bytes, token)
        else:
            attachments = data["attachments"]
            content = []
            for index, attach in enumerate(attachments):
                content.append(base64.b64decode(attach.pop("data")))
                attach["length"] = len(content[index])
            data_bytes = json.dumps(data).encode(self.ENCODING)
            result = self.do_request("/stacks/push", data_bytes, token)
            for attach in result["attachments"]:
                self.do_upload(attach["upload_url"], content[attach["index"]])
            result = result
        return result

    def access(self, stack: str, token: str) -> Dict:
        data_bytes = json.dumps({"stack": stack}).encode(self.ENCODING)
        return self.do_request("/stacks/access", data_bytes, token)

    def pull(self, stack: str, token: Optional[str], params: Optional[Dict]) -> Dict:
        params = {} if params is None else params
        url = f"/stacks/{stack}"
        res = self.do_request(url, None, token=token, method="GET")
        attachments = res["stack"]["head"]["attachments"]
        for index, attach in enumerate(attachments):
            if set(attach["params"].items()) == set(params.items()):
                frame = res["stack"]["head"]["id"]
                attach_url = f"/attachs/{stack}/{frame}/{index}?download=true"
                return self.do_request(attach_url, None, token=token, method="GET")
        raise MatchException(params)

    def do_request(self, endpoint: str, data_bytes: Optional[bytes], token: Optional[str], method: str = "POST") -> Dict:
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if data_bytes is None:
            response = requests.request(method=method, url=self.url + endpoint, headers=headers, verify=self.verify)
        else:
            headers["Content-Type"] = f"application/json; charset={self.ENCODING}"
            response = requests.request(method=method, url=self.url + endpoint, data=data_bytes, headers=headers, verify=self.verify)

        response.raise_for_status()
        return response.json(encoding=self.ENCODING)

    def download(self, url, filename):
        r = requests.get(url, stream=True, verify=self.verify)
        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)

    def do_upload(self, upload_url: str, data: bytes):
        response = requests.put(url=upload_url, data=data, verify=self.verify)
        response.raise_for_status()
