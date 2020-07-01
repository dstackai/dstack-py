import copy
import unittest
from typing import Dict, Optional

from dstack.config import Profile, InPlaceConfig, configure
from dstack.protocol import Protocol, ProtocolFactory, setup_protocol


class TestProtocol(Protocol):
    def __init__(self):
        self.exception = None
        self.data = None
        self.token = None

    def push(self, stack: str, token: str, data: Dict) -> Dict:
        data["stack"] = stack
        return self.handle(data, token)

    def access(self, stack: str, token: str) -> Dict:
        return self.handle({"stack": stack}, token)

    def pull(self, stack: str, token: Optional[str], params: Optional[Dict]) -> Dict:
        attachments = self.data["attachments"]
        for index, attach in enumerate(attachments):
            if (params is None and (len(attachments) == 1 or "params" not in attach)) or \
                    set(attach["params"].items()) == set(params.items()):
                d = attach.pop("data")
                attach1 = copy.deepcopy(attach)
                attach1["data"] = d.base64value()
                attach["data"] = d
                return {"attachment": attach1}

    def download(self, url):
        raise NotImplementedError()

    def handler(self, data: Dict, token: str) -> Dict:
        self.data = data
        self.token = token
        stack = data["stack"]
        return {"url": f"https://api.dstack.ai/{stack}"}

    def handle(self, data: Dict, token: str) -> Dict:
        if self.exception is not None:
            raise self.exception
        else:
            return self.handler(data, token)

    def broke(self, exception: Exception = RuntimeError()):
        self.exception = exception

    def fix(self):
        self.exception = None


class TestProtocolFactory(ProtocolFactory):
    def __init__(self, protocol: Protocol):
        self.protocol = protocol

    def create(self, profile: Profile) -> Protocol:
        return self.protocol


class TestBase(unittest.TestCase):
    def __init__(self, method: str = "runTest"):
        super().__init__(method)
        self.protocol = TestProtocol()

    def setUp(self):
        config = InPlaceConfig()
        config.add_or_replace_profile(Profile("default", "user", "my_token", "https://api.dstack.ai", verify=True))
        configure(config)
        self.protocol = TestProtocol()
        setup_protocol(TestProtocolFactory(self.protocol))
