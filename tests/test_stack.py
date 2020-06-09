import unittest

import matplotlib.pyplot as plt
import numpy as np

from dstack import create_frame, stack_path
from tests import TestBase


class StackFrameTest(TestBase):
    def test_cant_send_access(self):
        self.protocol.broke()
        try:
            create_frame(stack="plots/my_plot")
            self.fail("Error must be raised in send_access()")
        except RuntimeError:
            pass

    def test_single_plot(self):
        frame = create_frame(stack="plots/my_plot")
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        fig, ax = plt.subplots()
        ax.plot(t, s)
        my_desc = "My first plot"
        ax.set(xlabel="t", ylabel="x", title=my_desc)
        ax.grid()
        frame.commit(fig, my_desc)
        frame.push()

        attachments = self.protocol.data["attachments"]
        self.assertEqual("user/plots/my_plot", self.protocol.data["stack"])
        self.assertIsNotNone(self.protocol.data["id"])
        self.assertEqual("my_token", self.protocol.token)
        self.assertEqual(1, len(attachments))
        self.assertEqual("image/svg+xml", attachments[0]["content_type"])
        self.assertEqual("matplotlib", attachments[0]["application"])
        self.assertNotIn("params", attachments[0].keys())
        self.assertEqual(my_desc, attachments[0]["description"])

    def test_multiple_plots(self):
        frame = create_frame(stack="plots/my_plot")
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
        attachments = self.protocol.data["attachments"]
        self.assertEqual(len(p), len(attachments))
        for idx, phase in enumerate(p):
            att = attachments[idx]
            self.assertNotIn("description", att.keys())
            self.assertEqual(2, len(att["params"].keys()))
            self.assertEqual(idx, att["params"]["index"])
            self.assertEqual(phase, att["params"]["phase"])

    def test_stack_relative_path(self):
        frame = create_frame(stack="plots/my_plot")
        frame.commit(self.get_figure())
        frame.push()
        self.assertEqual(f"user/plots/my_plot", self.protocol.data["stack"])

    def test_stack_absolute_path(self):
        frame = create_frame(stack="/other/my_plot")
        frame.commit(self.get_figure())
        frame.push()
        self.assertEqual(f"other/my_plot", self.protocol.data["stack"])

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


if __name__ == '__main__':
    unittest.main()
