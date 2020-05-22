import base64
import io
from abc import ABC, abstractmethod
from typing import IO, Union


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


class StreamContent(Content):

    def __init__(self, input_stream: IO, content_length: int):
        self.input_stream = input_stream
        self.content_length = content_length
        self.cache = None

    def length(self) -> int:
        return self.content_length

    def stream(self) -> IO:
        return self.input_stream

    def value(self) -> bytes:
        if self.cache:
            return self.cache
        else:
            self.cache = self.input_stream.read()
            return self.cache
