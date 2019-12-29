import json
import unittest
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Callable

from dstack.matplotlib import MatplotlibHandler
from dstack.protocol import Protocol
from dstack.stack import create_frame


class TestProtocol(Protocol):
    def __init__(self, handler: Callable[[Dict], Dict]):
        self.exception = None
        self.handler = handler

    def send(self, endpoint: str, data: Dict) -> Dict:
        if self.exception is not None:
            raise self.exception
        else:
            return self.handler(data)

    def broke(self, exception: Exception = RuntimeError()):
        self.exception = exception

    def fix(self):
        self.exception = None


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

        ax.set(xlabel="t", ylabel="x", title="My first plot")
        ax.grid()

        my_desc = "My first plot"
        frame.commit(fig, my_desc)
        frame.push()

        attachments = self.data["attachments"]
        self.assertEqual("plots/my_plot", self.data["stack"])
        self.assertIsNotNone(self.data["id"])
        self.assertEqual("image/svg", self.data["type"])
        self.assertEqual("my_token", self.data["token"])
        self.assertEqual(1, len(attachments))
        self.assertFalse("params" in attachments[0].keys())
        self.assertEquals(my_desc, attachments[0]["description"])

    def handler(self, data: Dict) -> Dict:
        self.data = data
        print(json.dumps(data, indent=2))
        return {"status": 0}

    @staticmethod
    def setup_frame(protocol: Protocol, stack: str):
        return create_frame(stack=stack,
                            token='my_token',
                            handler=MatplotlibHandler(),
                            protocol=protocol)


if __name__ == '__main__':
    unittest.main()
