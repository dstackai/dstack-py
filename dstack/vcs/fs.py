import hashlib
import json
import os
import platform
from abc import ABC
from pathlib import Path
from typing import Optional, List, Dict, Any, Type

import numpy as np
import pandas as pd

from dstack import Context, _pull, create_context
from dstack import Encoder, FrameData, StreamContent, MediaType, Decoder, _push
from dstack.context import ContextAwareObject
from dstack.files.handlers import FileEncoder, FileDecoder
from dstack.pandas.handlers import DataFrameEncoder, DataFrameDecoder
from dstack.protocol import StackNotFoundError


class FileAttributes(object):
    def __init__(self, path: str, size: Optional[int], hash_code: Optional[str],
                 hash_alg: Optional[str], frame_id: Optional[str] = None):
        self.path = path
        self.size = size
        self.hash_code = hash_code
        self.hash_alg = hash_alg
        self.frame_id = frame_id

    def stack_path(self) -> str:
        hash_md5 = hashlib.md5()
        hash_md5.update(self.path.encode())
        return hash_md5.hexdigest()

    def __eq__(self, other) -> bool:
        return isinstance(other, FileAttributes) and \
               self.path == other.path and \
               self.size == other.size and \
               self.hash_code == other.hash_code and \
               self.hash_alg == other.hash_alg and \
               self.frame_id == self.frame_id

    def absolute_path(self, root: Path) -> Path:
        return FileSystem.absolute_path(root, self.path)

    def __repr__(self) -> str:
        return self.path


class WorkflowStateError(Exception, ABC):
    pass


class FileSystemIsAlreadyBoundedError(WorkflowStateError):
    def __init__(self, context: Context):
        self.context = context


class FileSystemIsNotInitializedError(WorkflowStateError):
    pass


class LocalChangesFoundError(WorkflowStateError):
    def __init__(self, conflicts: List[FileAttributes]):
        self.conflicts = conflicts


class Query(object):
    def __init__(self, query: str):
        self.query = query

    def search(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.query(self.query)


class FileSystemMetadata(object):
    def __init__(self, context: Context, root: Path, df: Optional[pd.DataFrame] = None):
        self.context = context
        self.root = root
        if df is None:
            df = pd.DataFrame({"path": [],
                               "size": [],
                               "hash_code": [],
                               "hash_alg": [],
                               "frame_id": []})

            schema = {"path": np.object,
                      "size": pd.Int64Dtype(),
                      "hash_code": np.object,
                      "hash_alg": np.object,
                      "frame_id": np.object}

            df = df.astype(schema)
            df.set_index("path", inplace=True)

        self.df = df

    def save(self):
        encoder = DataFrameEncoder()
        data = encoder.encode(self.df, description=None, params=None)

        if not self.system_path(self.root).exists():
            self.system_path(self.root).mkdir(parents=True)

        self.table_path(self.root).write_text(data.data.value().decode())

        data.settings["stack"] = self.context.stack
        data.settings["profile"] = self.context.profile.name

        with self.settings_path(self.root).open("w") as f:
            json.dump(data.settings, f)

    def chdir(self):
        os.chdir(str(self.root))

    def add(self, path: Path, meta: Optional[Dict[str, str]]):
        meta = meta or {}

        self.chdir()

        if path.is_dir():
            if not self.is_system_path(path):
                for file in path.iterdir():
                    self.add(file, meta)
        else:
            #  prepare system columns
            attr = {"path": [str(path)],
                    "size": [None],
                    "hash_code": [None],
                    "hash_alg": [None],
                    "frame_id": [None]}

            typed_meta = {}

            for k, v in meta.items():
                if k in attr:
                    # meta key is reserved
                    raise ValueError()

                dtype, typed_v = self.infer_type(v)

                if k not in self.df.columns:
                    self.df[k] = None
                    self.df[k] = self.df[k].astype(dtype=dtype)
                elif self.df[k].dtype != dtype:
                    raise ValueError()  # FIXME: user needs more information here

                typed_meta[k] = typed_v

            for k in self.df.columns:
                if k not in attr:
                    attr[k] = None

            # if the row exists remove it first and
            # optimize columns set to avoid completely empty columns
            path = str(path)
            old_meta = self.find(path)
            if old_meta and set(typed_meta) != set(old_meta):
                self.remove(path)

            schema = self.df.dtypes

            # add new row with all columns including typed meta
            attr.update(typed_meta)

            row = pd.DataFrame(attr).astype(schema)
            row.set_index("path", inplace=True)

            self.df = self.df.append(row, verify_integrity=True)

    def find(self, path: str) -> Optional[Dict[str, Any]]:
        result = {"path": path}
        row = self.df.loc[self.df.index == path]
        if not row.empty:
            # to_dict doesn't return the index
            result.update(row.to_dict("r")[0])

            for k, v in result.items():
                if v is pd.NA:
                    result[k] = None

            return result
        else:
            return None

    def remove(self, path: str):
        system_cols = ["path", "size", "hash_code", "hash_alg", "frame_id"]

        self.df = self.df.drop(index=path)

        # optimize column set: remove empty columns
        for col in self.df.columns:
            if col not in system_cols:
                if self.df[col].isnull().values.all():
                    self.df = self.df.drop(col, axis=1)

    @staticmethod
    def infer_type(value: str) -> (Type, Any):
        if value == "true" or value == "True":
            return np.bool, True
        elif value == "false" or value == "False":
            return np.bool, False
        else:
            try:
                return pd.Int64Dtype(), int(value)
            except ValueError:
                pass

            try:
                return np.float64, float(value)
            except ValueError:
                return np.object, value
        # FIXME: add datetime64 support

    def is_file_changed(self, attr: Optional[FileAttributes]) -> bool:
        if not attr:
            return False

        meta = self.find(attr.path)

        return meta is None or meta["hash_code"] != attr.hash_code

    def list(self, query: Optional[Query] = None) -> List[FileAttributes]:
        def or_none(r, col):
            val = r[col]
            # FIXME: bad solution
            return None if str(val) in ["nan", "<NA>"] else val

        result = []

        df = query.search(self.df) if query else self.df

        for index, row in df.iterrows():
            result.append(FileAttributes(str(index), or_none(row, "size"), or_none(row, "hash_code"),
                                         or_none(row, "hash_alg"), or_none(row, "frame_id")))

        return result

    def commit(self, attr: FileAttributes):
        old_attr = self.find(attr.path)
        for k, v in attr.__dict__.items():
            old_attr[k] = v

        old_attr = {k: [v] for k, v in old_attr.items()}
        row = pd.DataFrame(old_attr).astype(self.df.dtypes)
        self.df.update(row.set_index("path"))

    @staticmethod
    def load(path: Path) -> Optional['FileSystemMetadata']:
        table_path = FileSystemMetadata.table_path(path)

        if not table_path.exists():
            return None

        with table_path.open("r") as table_file:
            content = StreamContent(table_file, table_path.stat().st_size)

            with FileSystemMetadata.settings_path(path).open("r") as settings_file:
                settings = json.load(settings_file)
                decoder = DataFrameDecoder()
                df = decoder.decode(FrameData(content, media_type=MediaType("text/csv", "pandas/dataframe"),
                                              description=None, params=None, settings=settings))

        context = create_context(settings["stack"], settings["profile"])
        return FileSystemMetadata(context, path, df)

    @staticmethod
    def system_path(path: Path) -> Path:
        return path / ".dstack"

    @staticmethod
    def is_system_path(path: Path) -> bool:
        return path.name == ".dstack"

    @staticmethod
    def table_path(path: Path) -> Path:
        return FileSystemMetadata.system_path(path) / "filesystem.csv"

    @staticmethod
    def settings_path(path: Path) -> Path:
        return FileSystemMetadata.system_path(path) / "filesystem.json"


def inject_metadata(function):
    def wrapper(self, *args, metadata: Optional[FileSystemMetadata] = None, **kwargs):
        metadata = metadata or FileSystemMetadata.load(self.root)

        if not metadata:
            raise FileSystemIsNotInitializedError()

        result = function(self, *args, metadata=metadata, **kwargs)

        metadata.save()
        self.metadata = metadata

        return result

    return wrapper


class FileSystem(ContextAwareObject):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.metadata: Optional[FileSystemMetadata] = None

    def init(self, context: Context):
        metadata = FileSystemMetadata.load(self.root)

        if metadata:
            if context != metadata.context:
                raise FileSystemIsAlreadyBoundedError(metadata.context)
        else:
            FileSystemMetadata(context, self.root).save()

        self.set_context(context)

    @inject_metadata
    def add(self, files: List[Path], meta: Optional[Dict[str, Optional[str]]] = None,
            metadata: Optional[FileSystemMetadata] = None):
        for file in files:
            metadata.add(file, meta)

    @inject_metadata
    def changed_files(self, new_metadata: Optional[FileSystemMetadata] = None,
                      metadata: Optional[FileSystemMetadata] = None) -> List[FileAttributes]:
        result = []

        for file in metadata.list():
            attr = self.attributes(file.path)
            if attr and (not new_metadata or new_metadata.is_file_changed(attr)):
                result.append(attr)

        return result

    @inject_metadata
    def push(self, metadata: Optional[FileSystemMetadata] = None):
        _push(metadata.context, self, encoder=FileSystemEncoder())
        metadata.df = self.metadata.df

    @inject_metadata
    def fetch(self, metadata: Optional[FileSystemMetadata] = None):
        if not metadata:
            raise FileSystemIsNotInitializedError()

        fs: FileSystem = _pull(metadata.context, decoder=FileSystemDecoder(self.root))
        metadata.df = fs.metadata.df

    def checkout(self, context: Context):
        self.init(context)
        self.fetch()

    @inject_metadata
    def commit(self, changes: List[FileAttributes], metadata: Optional[FileSystemMetadata] = None):
        for attr in changes:
            metadata.commit(attr)

    @inject_metadata
    def pull(self, query: Optional[Query] = None, force: bool = False, metadata: Optional[FileSystemMetadata] = None):
        context = metadata.context
        conflicts = []

        files = metadata.list(query)
        for file in files:
            attr = self.attributes(file.path)
            if metadata.is_file_changed(attr):
                conflicts.append(attr)

        if conflicts and not force:
            raise LocalChangesFoundError(conflicts)

        for file in files:
            file_context = context.derive(f"{context.stack}/{file.stack_path()}")
            _pull(file_context, decoder=FileAttributesDecoder(self.root / file.path))

    @inject_metadata
    def list(self, query: Optional[Query] = None, metadata: Optional[FileSystemMetadata] = None) -> List[FileAttributes]:
        return metadata.list(query=query)

    def attributes(self, relative_path: str) -> Optional[FileAttributes]:
        path = self.absolute_path(self.root, relative_path)

        if not path.exists():
            return None

        size = path.lstat().st_size
        md5hash = self.md5hash(path)

        return FileAttributes(relative_path, size, md5hash, "md5")

    @staticmethod
    def absolute_path(root: Path, relative_path: str) -> Path:
        return root / (relative_path if platform.system() != "Windows" else relative_path.replace('/', '\\'))

    @staticmethod
    def md5hash(path: Path) -> str:
        hash_md5 = hashlib.md5()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def num_files(self) -> int:
        return len(self.metadata.list())

    @inject_metadata
    def files_changed(self, metadata: Optional[FileSystemMetadata] = None) -> List[str]:
        result = []

        for file in metadata.list():
            attr = self.attributes(file.path)
            if file.hash_code != attr.hash_code:
                result.append(file.path)

        return result


class FileSystemEncoder(Encoder[FileSystem]):
    def encode(self, obj: FileSystem, description: Optional[str], params: Optional[Dict]) -> FrameData:
        context = self.get_context()
        fs: Optional[FileSystem] = None

        try:
            # do not pull actual files, only metadata
            fs = _pull(context, decoder=FileSystemDecoder(obj.root))
        except StackNotFoundError:
            pass

        changes = []
        for file in obj.changed_files(fs.metadata if fs else None):
            print(f"Pushing {file.path}")
            file_context = context.derive(f"{context.stack}/{file.stack_path()}")
            res = _push(file_context, file, encoder=FileAttributesEncoder(obj.root))
            file.frame_id = res.id
            changes.append(file)

        obj.commit(changes)

        encoder = DataFrameEncoder()
        result = encoder.encode(obj.metadata.df, description, params)
        result.application = "filesystem"
        return result


class FileSystemDecoder(Decoder[FileSystem]):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root

    def decode(self, data: FrameData) -> FileSystem:
        context = self.get_context()
        decoder = DataFrameDecoder()
        df = decoder.decode(data)
        fs = FileSystem(self.root)
        fs.set_context(context)
        fs.metadata = FileSystemMetadata(context, self.root, df)
        return fs


class FileAttributesEncoder(Encoder[FileAttributes]):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root

    def encode(self, obj: FileAttributes, description: Optional[str], params: Optional[Dict]) -> FrameData:
        encoder = FileEncoder(obj.__dict__)
        return encoder.encode(obj.absolute_path(self.root), description, params)


class FileAttributesDecoder(Decoder[FileAttributes]):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def decode(self, data: FrameData) -> FileAttributes:
        decoder = FileDecoder(self.path)
        decoder.decode(data)
        return FileAttributes(data.settings["path"], data.settings["size"],
                              data.settings["hash_code"], data.settings["hash_alg"])
