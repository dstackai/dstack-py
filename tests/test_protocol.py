import base64
import copy
import json
import os
import time
from unittest import TestCase
from unittest.mock import patch

from dstack import JsonProtocol, BytesContent
import numpy as np
from sklearn import datasets
from sklearn.linear_model import LinearRegression
import dstack as ds
from dstack.util import HOME_CACHE_DIR


class TestJsonProtocol(TestCase):
    def test_data_base64_length(self):
        def test_b64(s: str):
            buf = s.encode("UTF-8")
            data = BytesContent(buf)
            self.assertEqual(len(base64.b64encode(buf)), data.base64length())

        tests = ["hello world", "привет мир!"]
        for t in tests:
            test_b64(t)

    def test_length(self):
        def b64(d):
            d["data"] = base64.b64encode(d["data"].value()).decode()

        def length(d) -> int:
            x = copy.deepcopy(d)
            for attach in x["attachments"]:
                b64(attach)
            return len(json.dumps(x).encode(protocol.ENCODING))

        data = {
            "name": "my name",
            "x": 10,
            "attachments": [
                {
                    "data": BytesContent(b"test test"),
                    "hello": "world"
                },
                {
                    "data": BytesContent(b"hello world"),
                    "hello": "world"
                }
            ]
        }
        protocol = JsonProtocol("http://myhost", True)
        self.assertEqual(protocol.length(data), length(data))

    def modeling(self) -> str:
        diabetes_X, diabetes_y = datasets.load_diabetes(return_X_y=True)
        diabetes_X = diabetes_X[:, np.newaxis, 2]
        diabetes_X_train = diabetes_X[:-20]
        # diabetes_X_test = diabetes_X[-20:]
        diabetes_y_train = diabetes_y[:-20]
        # diabetes_y_test = diabetes_y[-20:]
        regr = LinearRegression()
        regr.fit(diabetes_X_train, diabetes_y_train)

        # def unique stack_name
        stack_name = str(hash(time.time()))
        ds.push(stack_name, regr)
        my_model_0 = ds.pull(stack_name)

        return stack_name

    def get_dict_by_stack_name(self, stack_name) -> dict:
        # return dict from unique stack_name (find file in home-cache-dir)

        subdirs = [x[0] for x in os.walk(HOME_CACHE_DIR)]
        needed_subdirs = []
        for dir in subdirs:
            if stack_name in dir:
                needed_subdirs.append([dir, len(dir)])
        path_to_ans = os.path.join(sorted(needed_subdirs, key=lambda x: x[1])[-1][0], 'dict')
        with open(path_to_ans, 'r') as f:
            value = json.load(f)
        return value

    def test_pull_v0(self):

        stack_name = self.modeling()
        value = self.get_dict_by_stack_name(stack_name)

        @patch('dstack.protocol.json.loads', autospec=True)
        def test_loads(mock_protocol_json_loads):

            mock_protocol_json_loads.return_value = value

            pulled_model = ds.pull(stack_name)
            mock_protocol_json_loads.assert_called_once()

        test_loads()
