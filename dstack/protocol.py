import base64
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional

import requests

import dstack.logger as log
from dstack.config import Profile


class MatchException(ValueError):
    def __init__(self, params: Dict):
        self.params = params

    def __str__(self):
        return f"Can't match parameters {self.params}"


class Protocol(ABC):
    @abstractmethod
    def push(self, stack: str, token: str, data: Dict) -> Dict:
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

    def push(self, stack: str, token: str, data: Dict) -> Dict:
        data["stack"] = stack
        size = self.length(data)
        if size < self.MAX_SIZE:
            result = self.do_request("/stacks/push", data, token)
        else:
            attachments = data["attachments"]
            content = []
            for index, attach in enumerate(attachments):
                content.append(base64.b64decode(attach.pop("data")))
                attach["length"] = len(content[index])
            result = self.do_request("/stacks/push", data, token)
            for attach in result["attachments"]:
                self.do_upload(attach["upload_url"], content[attach["index"]])
            result = result
        return result

    def access(self, stack: str, token: str) -> Dict:
        return self.do_request("/stacks/access", {"stack": stack}, token)

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

    def do_request(self, endpoint: str, data: Optional[Dict], token: Optional[str], method: str = "POST") -> Dict:
        url = self.url + endpoint

        event_id = log.uuid()
        log.debug(event_id=event_id, func=log.erase_sensitive_data, url=url, method=method, data=data)

        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if data is None:
            response = requests.request(method=method, url=url,
                                        headers=headers, verify=self.verify)
        else:
            data_bytes = json.dumps(data).encode(self.ENCODING)
            headers["Content-Type"] = f"application/json; charset={self.ENCODING}"
            response = requests.request(method=method, url=url, data=data_bytes,
                                        headers=headers, verify=self.verify)

        log.debug(event_id=event_id, func=log.erase_token, request_headers=response.request.headers)
        log.debug(event_id=event_id, func=log.ensure_json_serialization, response_headers=response.headers)

        response.raise_for_status()
        return response.json(encoding=self.ENCODING)

    def download(self, url, filename):
        r = requests.get(url, stream=True, verify=self.verify)

        log.debug(func=log.ensure_json_serialization, url=url, reponse_headers=r.headers)

        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=65536):
                fd.write(chunk)

    def do_upload(self, upload_url: str, data: bytes):
        event_id = log.uuid()
        log.debug(event_id=event_id, url=upload_url, length=len(data))

        response = requests.put(url=upload_url, data=data, verify=self.verify)

        log.debug(event_id=event_id, func=log.ensure_json_serialization, request_headers=response.request.headers)
        log.debug(event_id=event_id, func=log.ensure_json_serialization, response_headers=response.headers)

        response.raise_for_status()

    def length(self, data: Dict):
        return len(json.dumps(data).encode(self.ENCODING))


class ProtocolFactory(ABC):
    @abstractmethod
    def create_protocol(self, profile: Profile) -> Protocol:
        pass


class JsonProtocolFactory(ProtocolFactory):
    def create_protocol(self, profile: Profile) -> Protocol:
        return JsonProtocol(profile.server, profile.verify)


__protocol_factory = JsonProtocolFactory()


def setup_protocol(protocol_factory: ProtocolFactory):
    global __protocol_factory
    __protocol_factory = protocol_factory


def create_protocol(profile: Profile) -> Protocol:
    return __protocol_factory.create_protocol(profile)
