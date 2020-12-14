import os
import time
import unittest
import dstack as ds
from dstack.util import HOME_CACHE_DIR
from tests import TestBase


@ds.util.flash_cache(cache_dir=HOME_CACHE_DIR)
def some_huge_fun(_a: int, _b: str):
    time.sleep(1)
    return _a, _b


class TestUtil(TestBase):
    def test_empty_prepare_for_hash(self):
        self.assertEqual(ds.util.prepare_for_hash(), '0')

    def test_prepare_for_hash_args(self):
        args = ['a', 1, ('b', '1')]
        expectation = "('a', 1, ('b', '1')){}"
        self.assertEqual(ds.util.prepare_for_hash(*args), expectation)

    def test_prepare_for_hash_kwargs(self):
        kwargs = {'a': 1, 'b': '1'}
        expectation = '(){"a": 1, "b": "1"}'
        self.assertEqual(ds.util.prepare_for_hash(**kwargs), expectation)

    def test_prepare_for_hash_args_kwargs(self):
        args = ['a', 1, ('b', '1')]
        kwargs = {'a': 1, 'b': '1'}
        expectation = "('a', 1, ('b', '1'))" + '{"a": 1, "b": "1"}'
        self.assertEqual(ds.util.prepare_for_hash(*args, **kwargs), expectation)

    def test_get_filename(self):
        s = 'some_string'
        expectation = '31ee76261d87fed8cb9d4c465c48158c'
        self.assertEqual(ds.util.get_filename(s), expectation)

    def test_flash_cache_speed(self):
        a = int(round(time.time() * 1000))
        b = str(int(round(time.time() * 1000)))

        t0 = time.time()
        first_return = some_huge_fun(a, b)
        t1 = time.time()
        first_call = t1 - t0

        t0 = time.time()
        second_return = some_huge_fun(a, b)
        t1 = time.time()
        second_call = t1 - t0

        # should be minimum 10th times faster:
        is_faster = second_call * 10 < first_call

        self.assertEqual(is_faster, True)

    def test_flash_cache_same_result(self):
        a = int(round(time.time() * 1000))
        b = str(int(round(time.time() * 1000)))

        first_return = some_huge_fun(a, b)
        second_return = some_huge_fun(a, b)

        self.assertEqual(first_return, second_return)

    def test_flash_cache_files(self):
        a = int(round(time.time() * 1000))
        b = str(int(round(time.time() * 1000)))

        n_files_in_dir_before = len(os.listdir(HOME_CACHE_DIR))

        first_return = some_huge_fun(a, b)
        second_return = some_huge_fun(a, b)

        n_files_in_dir_after = len(os.listdir(HOME_CACHE_DIR))

        self.assertEqual(n_files_in_dir_after, n_files_in_dir_before + 1)


if __name__ == '__main__':
    unittest.main()
