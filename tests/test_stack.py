import json
import unittest
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Callable

from dstack.matplotlib import MatplotlibHandler
from dstack.protocol import Protocol
from dstack.stack import StackFrame


class TestProtocol(Protocol):
    def __init__(self, handler: Callable[[Dict], Dict]):
        self.exception = None
        self.handler = handler

    def send(self, data: Dict) -> Dict:
        if self.exception is not None:
            raise self.exception
        else:
            return self.handler(data)

    def broke(self, exception: Exception):
        self.exception = exception

    def fix(self):
        self.exception = None


class StackFrameTest(unittest.TestCase):
    def test_single_plot(self):
        protocol = self.setup_protocol()
        frame = StackFrame(stack='plots/simple_plot',
                           token='token',
                           handler=MatplotlibHandler(),
                           protocol=protocol)

        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)

        fig, ax = plt.subplots()
        ax.plot(t, s)

        ax.set(xlabel='t', ylabel='x',
               title='My first plot')
        ax.grid()

        frame.commit(fig, 'My first plot')
        frame.push()

    @staticmethod
    def setup_protocol() -> Protocol:
        def handler(data: Dict) -> Dict:
            print(json.dumps(data, indent=2))
            return {"status": 0}

        return TestProtocol(handler)


if __name__ == '__main__':
    unittest.main()
