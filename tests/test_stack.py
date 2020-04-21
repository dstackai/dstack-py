import json
import unittest
from typing import Dict, Callable, Optional

import matplotlib.pyplot as plt
import numpy as np

from dstack import create_frame, configure, stack_path
from dstack.config import Profile, InPlaceConfig
from dstack.protocol import Protocol


class TestProtocol(Protocol):
    def __init__(self, handler: Callable[[Dict, str], Dict]):
        self.exception = None
        self.handler = handler

    def push(self, stack: str, token: str, data: Dict) -> Dict:
        data["stack"] = stack
        return self.handle(data, token)

    def access(self, stack: str, token: str) -> Dict:
        return self.handle({"stack": stack}, token)

    def pull(self, stack: str, token: Optional[str], params: Optional[Dict]) -> Dict:
        pass

    def download(self, url, filename):
        pass

    def handle(self, data: Dict, token: str) -> Dict:
        if self.exception is not None:
            raise self.exception
        else:
            return self.handler(data, token)

    def broke(self, exception: Exception = RuntimeError()):
        self.exception = exception

    def fix(self):
        self.exception = None


class TestConfig(InPlaceConfig):
    def __init__(self, protocol: Protocol):
        super().__init__()
        self.protocol = protocol

    def create_protocol(self, profile: Profile) -> Protocol:
        return self.protocol


class StackFrameTest(unittest.TestCase):
    def test_cant_send_access(self):
        protocol = TestProtocol(self.handler)
        protocol.broke()
        try:
            self.setup_frame(protocol, stack="plots/my_plot")
            self.fail("Error must be raised in send_access()")
        except RuntimeError:
            pass

    def test_single_plot(self):
        protocol = TestProtocol(self.handler)
        frame = self.setup_frame(protocol, stack="plots/my_plot")
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        fig, ax = plt.subplots()
        ax.plot(t, s)
        my_desc = "My first plot"
        ax.set(xlabel="t", ylabel="x", title=my_desc)
        ax.grid()
        frame.commit(fig, my_desc)
        frame.push()

        attachments = self.data["attachments"]
        self.assertEqual("user/plots/my_plot", self.data["stack"])
        self.assertIsNotNone(self.data["id"])
        self.assertEqual("my_token", self.token)
        self.assertEqual(1, len(attachments))
        self.assertEqual("image/svg", attachments[0]["type"])
        self.assertNotIn("params", attachments[0].keys())
        self.assertEqual(my_desc, attachments[0]["description"])

    def test_multiple_plots(self):
        protocol = TestProtocol(self.handler)
        frame = self.setup_frame(protocol, stack="plots/my_plot")
        p = np.arange(0.0, 1.0, 0.1)

        for idx, phase in enumerate(p):
            t = np.arange(0.0, 2.0, 0.01)
            s = 1 + np.sin(2 * np.pi * t + phase)
            fig, ax = plt.subplots()
            ax.plot(t, s)
            ax.set(xlabel="t", ylabel="x", title="Plot with parameters")
            ax.grid()
            frame.commit(fig, params={"phase": phase, "index": idx})

        frame.push()
        attachments = self.data["attachments"]
        self.assertEqual(len(p), len(attachments))
        for idx, phase in enumerate(p):
            att = attachments[idx]
            self.assertNotIn("description", att.keys())
            self.assertEqual(2, len(att["params"].keys()))
            self.assertEqual(idx, att["params"]["index"])
            self.assertEqual(phase, att["params"]["phase"])

    def test_stack_relative_path(self):
        protocol = TestProtocol(self.handler)
        frame = self.setup_frame(protocol, stack="plots/my_plot")
        frame.commit(self.get_figure())
        frame.push()
        self.assertEqual(f"user/plots/my_plot", self.data["stack"])

    def test_stack_absolute_path(self):
        protocol = TestProtocol(self.handler)
        frame = self.setup_frame(protocol, stack="/other/my_plot")
        frame.commit(self.get_figure())
        frame.push()
        self.assertEqual(f"other/my_plot", self.data["stack"])

    def test_stack_path(self):
        self.assertEqual("test/project11/good_stack", stack_path("test", "project11/good_stack"))
        self.assertFailed(stack_path, "test", "плохой_стек")
        self.assertFailed(stack_path, "test", "bad stack")

    def assertFailed(self, func, *args):
        try:
            func(*args)
            self.fail()
        except ValueError:
            pass

    @staticmethod
    def get_figure():
        fig = plt.figure()
        plt.plot([1, 2, 3, 4], [1, 4, 9, 16])
        return fig

    def handler(self, data: Dict, token: str) -> Dict:
        self.data = data
        self.token = token
        print(json.dumps(data, indent=2))
        return {"status": 0, "url": "https://api.dstack.ai/stacks/test/test"}

    @staticmethod
    def setup_frame(protocol: Protocol, stack: str):
        config = TestConfig(protocol)
        config.add_or_replace_profile(Profile("default", "user", "my_token", "https://api.dstack.ai", verify=True))
        configure(config)
        return create_frame(stack=stack)


if __name__ == '__main__':
    unittest.main()
