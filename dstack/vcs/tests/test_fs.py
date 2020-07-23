import tempfile
from pathlib import Path
from typing import List, Union, Dict
from uuid import uuid4

import numpy as np
import pandas as pd

from dstack import create_context
from dstack.vcs.fs import FileSystem, FileSystemMetadata
from tests import TestBase


class TestFileSystem(TestBase):
    def setUp(self):
        super().setUp()
        # FIXME: reuse it
        self.temp = Path(tempfile.gettempdir()) / f"dstack-f{uuid4()}"

    def test_find(self):
        base = self.absolute_path("mydir")

        context = create_context("mystack")

        data = {"path": ["file1", "file2", "file3"],
                "size": [None, None, None],
                "hash_code": [None, None, None],
                "hash_alg": [None, None, None],
                "frame_id": [None, None, None],
                "tag1": [1, 2, 3],
                "tag2": ["A", "B", "C"]}

        df = pd.DataFrame(data).astype({
            "path": np.object,
            "size": pd.Int64Dtype(),
            "hash_code": np.object,
            "hash_alg": np.object,
            "frame_id": np.object,
            "tag1": pd.Int64Dtype(),
            "tag2": np.object
        })

        df.set_index("path", inplace=True)
        metadata = FileSystemMetadata(context, base, df)
        self.assertTrue({"path": "file2", "size": None, "hash_code": None,
                         "hash_alg": None, "frame_id": None, "tag1": 2, "tag2": "A"}, metadata.find("file2"))

        self.assertIsNone(metadata.find("file4"))

    def test_remove(self):
        base = self.absolute_path("mydir")
        context = create_context("mystack")

        data = {"path": ["file1", "file2", "file3"],
                "size": [None, None, None],
                "hash_code": [None, None, None],
                "hash_alg": [None, None, None],
                "frame_id": [None, None, None],
                "tag1": [1, None, None],
                "tag2": ["A", None, None],
                "tag3": [2, 4, None]}

        df = pd.DataFrame(data)
        df = df.set_index("path")
        metadata = FileSystemMetadata(context, base, df)

        # tag1 and tag2 should disappear
        metadata.remove("file1")
        self.assertIsNone(metadata.find("file1"))
        self.assertNotIn("tag1", metadata.df.columns)
        self.assertNotIn("tag2", metadata.df.columns)
        self.assertIn("tag3", metadata.df.columns)

        # check system columns
        self.assertIn("path", metadata.df.index.name)
        self.assertIn("size", metadata.df.columns)
        self.assertIn("hash_code", metadata.df.columns)
        self.assertIn("hash_alg", metadata.df.columns)
        self.assertIn("frame_id", metadata.df.columns)

    def test_infer_type(self):
        base = self.absolute_path("mydir")
        context = create_context("mystack")

        metadata = FileSystemMetadata(context, base)
        self.assertEqual((np.object, "hello"), metadata.infer_type("hello"))
        self.assertEqual((pd.Int64Dtype(), 10), metadata.infer_type("10"))
        self.assertEqual((np.float64, 1.3), metadata.infer_type("1.3"))
        self.assertEqual((np.bool, True), metadata.infer_type("true"))
        self.assertEqual((np.bool, False), metadata.infer_type("false"))
        self.assertEqual((np.bool, True), metadata.infer_type("True"))
        self.assertEqual((np.bool, False), metadata.infer_type("False"))

        # FIXME: check datetime64 support
        # self.assertEqual(("datetime64", "hello"), metadata.infer_type("hello"))

    def test_add(self):
        base = self.absolute_path("mydir")
        self.create_some_files(base)

        # os.chdir(str(base))

        fs = FileSystem(base)
        context = create_context("mystack")
        fs.init(context)
        dot = Path(".")
        fs.add([dot / "file1.txt"])
        self.assertEqual((1, 4), fs.metadata.df.shape)  # +1 for index

        self.assertEqual({"size": "Int64",
                          "hash_code": "object",
                          "hash_alg": "object",
                          "frame_id": "object"}, self.schema(fs.metadata.df))

        attr = fs.metadata.find("file1.txt")
        self.assertEqual({"path": "file1.txt",
                          "size": None,
                          "hash_code": None,
                          "hash_alg": None,
                          "frame_id": None}, attr)

        fs.add([dot / "file2.txt"], {"tag1": "4", "tag2": "true"})

        self.assertEqual({"size": "Int64",
                          "hash_code": "object",
                          "hash_alg": "object",
                          "frame_id": "object",
                          "tag1": "Int64",
                          "tag2": "bool"}, self.schema(fs.metadata.df))

        fs.add([dot / "subdir1"], {"tag3": "Hello"})

        self.assertEqual({"size": "Int64",
                          "hash_code": "object",
                          "hash_alg": "object",
                          "frame_id": "object",
                          "tag1": "Int64",
                          "tag2": "bool",
                          "tag3": "object"}, self.schema(fs.metadata.df))

    def test_commit_and_list(self):
        base = self.absolute_path("mydir")
        self.create_some_files(base)

        # os.chdir(str(base))

        fs = FileSystem(base)
        context = create_context("mystack")
        fs.init(context)
        dot = Path(".")
        tags = {"tag1": "1.0", "tag2": "test"}
        fs.add([dot / "file1.txt"], tags)

        attr = fs.attributes("file1.txt")
        attr.frame_id = "123"
        fs.commit([attr])

        self.assertEqual({"frame_id": "123",
                          "hash_alg": "md5",
                          "hash_code": "cef7ccd89dacf1ced6f5ec91d759953f",
                          "path": "file1.txt",
                          "size": 5,
                          "tag1": 1.0,
                          "tag2": "test"}, fs.metadata.find("file1.txt"))

        fs.add([dot / "subdir2"], {"tag3": "10"})
        attr2 = fs.attributes("subdir2/file5.txt")
        attr2.frame_id = "124"
        attr3 = fs.attributes("subdir2/file6.txt")
        attr3.frame_id = "125"

        fs.commit([attr2, attr3])
        self.assertIsNotNone(fs.metadata.find("subdir2/file5.txt"))
        self.assertIsNotNone(fs.metadata.find("subdir2/file6.txt"))

        files = sorted(fs.metadata.list(), key=lambda x: x.path)
        attrs = sorted([attr, attr2, attr3], key=lambda x: x.path)
        self.assertEqual(attrs, files)
        print(fs.metadata.df)

    @staticmethod
    def schema(df: pd.DataFrame) -> Dict[str, str]:
        return dict(zip(df.columns, [str(x) for x in df.dtypes]))

    def test_simple_checkout(self):
        base = self.absolute_path("mydir")
        self.create_some_files(base)

        # we should add relative paths
        dot = Path(".")
        fs = FileSystem(base)
        context = create_context("mystack")
        fs.init(context)
        fs.add([dot / "file1.txt"])
        fs.add([dot / "subdir1" / "file4.txt"])
        fs.push()

        dest = self.absolute_path("dest")

        # checkout
        fs1 = FileSystem(dest)
        fs1.checkout(context)

        self.assertEqual(2, fs1.num_files())
        fs1.pull()

        file1 = dest / "file1.txt"
        file4 = dest / "subdir1" / "file4.txt"
        self.assertTrue(file1.exists())
        self.assertEqual("text1", file1.read_text())
        self.assertTrue(file4.exists())
        self.assertEqual("text4", file4.read_text())

    def test_files_changed(self):
        base = self.absolute_path("mydir")

        files = self.create_some_files(base)
        # os.chdir(str(base))

        context = create_context("myfs")

        # push all files
        dot = Path(".")
        fs = FileSystem(self.absolute_path(base))
        fs.init(context)
        fs.add([dot])

        # print(fs.metadata.df)

        changed = fs.files_changed()
        fs.push()
        self.assertEqual(len(files), fs.num_files())
        self.assertEqual(set(files), set(changed))

        dest = self.absolute_path("dest")
        dest.mkdir(parents=True)
        # os.chdir(str(dest))
        fs1 = FileSystem(dest)
        fs1.checkout(context)

        self.assertEqual(len(files), fs1.num_files())
        fs1.pull()

        import glob

        for filename in glob.iglob(str(base) + '**/**', recursive=True):
            relative = Path(filename).relative_to(base)
            if not relative.is_dir():
                dest_file = dest / relative
                self.assertTrue(dest_file.exists())
                self.assertEqual(Path(filename).read_text(), dest_file.read_text())

        self.create_file(base, Path("file2.txt"), "text2__")
        self.create_file(base, Path("subdir1") / "file4.txt", "text4__")

        # push changes
        fs = FileSystem(base)
        fs.set_context(context)
        # os.chdir(str(base))

        self.assertEqual({'file2.txt', 'subdir1/file4.txt'}, set(fs.files_changed()))

        fs.push()
        self.assertEqual(len(files), fs.num_files())

        fs1 = FileSystem(dest)
        fs.set_context(context)
        # os.chdir(str(base))

        fs1.fetch()
        print(fs1.metadata.df)
        # fs1.pull_files()
        self.assertEqual({'file2.txt', 'subdir1/file4.txt'}, set(fs1.files_changed()))

    def create_file(self, base: Path, relative_path: Path, text: str) -> str:
        path = base / relative_path
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        path.write_text(text)
        return str(relative_path)

    def read_file(self, path: Path) -> str:
        return (self.temp / path).read_text()

    def absolute_path(self, path: Union[Path, str]) -> Path:
        return self.temp / path

    def create_some_files(self, base: Path) -> List[str]:
        return [self.create_file(base, Path("file1.txt"), "text1"),
                self.create_file(base, Path("file2.txt"), "text2"),
                self.create_file(base, Path("subdir1") / "file3.txt", "text3"),
                self.create_file(base, Path("subdir1") / "file4.txt", "text4"),
                self.create_file(base, Path("subdir2") / "file5.txt", "text5"),
                self.create_file(base, Path("subdir2") / "file6.txt", "text6")]
