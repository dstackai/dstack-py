import base64
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Union, Optional


class Content(ABC):
    @abstractmethod
    def length(self) -> int:
        pass

    def base64length(self) -> int:
        return (int(4 * self.length() / 3) + 3) & ~3

    @abstractmethod
    def stream(self) -> IO:
        pass

    @abstractmethod
    def value(self) -> bytes:
        pass

    def base64value(self) -> str:
        return base64.b64encode(self.value()).decode("utf-8")


class BytesContent(Content):
    def __init__(self, buf: Union[bytes, io.BytesIO]):
        self.buf = buf if isinstance(buf, io.BytesIO) else io.BytesIO(buf)

    def length(self) -> int:
        return self.buf.getbuffer().nbytes

    def stream(self) -> IO:
        return self.buf

    def value(self) -> bytes:
        return self.buf.getvalue()


class AbstractStreamContent(Content, ABC):
    def __init__(self):
        self.cache = None

    def value(self) -> bytes:
        if self.cache:
            return self.cache
        else:
            self.cache = self.stream().read()
            return self.cache


class StreamContent(AbstractStreamContent):
    def __init__(self, input_stream: IO, content_length: int):
        super().__init__()
        self.input_stream = input_stream
        self.content_length = content_length

    def length(self) -> int:
        return self.content_length

    def stream(self) -> IO:
        return self.input_stream


class FileContent(AbstractStreamContent):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def length(self) -> int:
        return Path(self.filename).stat().st_size

    def stream(self) -> IO:
        return open(self.filename, "r")


class MediaType(object):
    content_type_map = {
        "application/json": "json",
        "image/png": "png",
        "image/svg+xml": "svg",
        "text/csv": "csv"
    }

    def __init__(self, content_type: str, application_type: str, storage_format: Optional[str] = None):
        self.content_type = content_type
        self.application_type = application_type
        self.storage_format = storage_format if storage_format else self.content_type_map.get(content_type, None)
