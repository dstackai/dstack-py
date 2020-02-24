import base64
import io
import time
from abc import ABC, abstractmethod
from platform import uname
from typing import Dict, List, Optional
from uuid import uuid4

from dstack.protocol import Protocol

# PEP 440
__version__ = "0.1.0"


class FrameData:
    """Represents frame data structure which will be attached to stack frame by `commit` and can be sent by protocol
    implementation, as JSON for example. Every frame can contain many `FrameData` objects, any such object represent
    a piece of data user is going to publish, e.g. a chart with specified parameters.
    Every frame must have at least one `FrameData` object attached.
    Any handler must produce `FrameData` from raw data, like Matplotlib `Figure` or any other chart object.
    """

    def __init__(self, data: io.BytesIO,
                 description: Optional[str],
                 params: Optional[Dict],
                 settings: Optional[Dict] = None):
        """Creates frame data.
        Args:
            data: A binary representation of the object to be displayed.
            description: Optional description.
            params: A dictionary with parameters which will be used to produce appropriate controls.
            settings: Optional settings are usually used to store libraries versions or extra information
                required to display data correctly.
        """
        self.data = str(base64.b64encode(data.getvalue()))[2:-1]
        self.description = description
        self.params = params
        self.settings = settings


class Handler(ABC):
    """To be able to publish data it's necessary to have a suitable binary representation. This is a base class for all
    handlers. Many useful representations are supported including popular formats such as PNG and SVG. Moreover popular
    JavaScript-based libraries like Plotly and Bokeh are supported as well.
    """
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg"
    PLOTLY = "plotly"
    BOKEH = "bokeh"

    @abstractmethod
    def to_frame_data(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Converts data object to appropriate format.
        Args:
            obj: A data which is needed to be converted, e.g. plot.
            description: Description of the data.
            params: Parameters of the data, which are needed to be displayed,
                e.g. plot or model settings.

        Returns:
            Frame data.
        """
        pass

    @abstractmethod
    def media_type(self) -> str:
        """Supported media type.

        Returns:
            One of the following supported media types with corresponding constants:
            `IMAGE_PNG` refers to "image/png" and represents PNG images
            `IMAGE_SVG` refers to "image/svg" and represents SVG images
            `PLOTLY`    refers to "plotly" and represents Plotly chart as JSON
            `BOKEH`     refers to "bokeh" and represents Bokeh chart as JSON
        """
        pass


class EncryptionMethod(ABC):
    @abstractmethod
    def encrypt(self, frame: FrameData) -> FrameData:
        pass

    @abstractmethod
    def info(self) -> Dict:
        pass


class NoEncryption(EncryptionMethod):
    def encrypt(self, frame: FrameData) -> FrameData:
        return frame

    def info(self) -> Dict:
        return {}


class StackFrame(object):
    def __init__(self,
                 stack: str,
                 user: str,
                 token: str,
                 handler: Handler,
                 auto_push: bool,
                 protocol: Protocol,
                 encryption: EncryptionMethod):
        self.stack = stack
        self.user = user
        self.token = token
        self.auto_push = auto_push
        self.protocol = protocol
        self.encryption_method = encryption
        self.id = uuid4().__str__()
        self.index = 0
        self.handler = handler
        self.timestamp = int(round(time.time() * 1000))  # milliseconds
        self.data: List[FrameData] = []

    def commit(self, obj, description: Optional[str] = None, params: Optional[Dict] = None):
        """Adds data to the stack frame.

        Args:
            obj: A data to commit. Data will be preprocessed by the handler but dependently on auto_push
                mode will be sent to server or not. If auto_push is False then the data won't be sent.
                Explicit push call need anyway to process committed data. auto_push is useful only in the
                case of multiple data objects in the stack frame, e.g. set of plots with settings.
            description: Description of the data.
            params: Parameters associated with this data, e.g. plot settings.
        """
        data = self.handler.to_frame_data(obj, description, params)
        encrypted_data = self.encryption_method.encrypt(data)
        self.data.append(encrypted_data)
        if self.auto_push:
            self.push_data(encrypted_data)

    def push(self) -> str:
        """Pushes all commits to server. In the case of auto_push mode it sends only a total number
        of elements in the frame. So call this method is obligatory to close frame anyway.

        Returns:
            Stack URL.
        """
        frame = self.new_frame()
        if not self.auto_push:
            frame["attachments"] = [filter_none(x.__dict__) for x in self.data]
            return self.send_push(frame)
        else:
            frame["total"] = self.index
            return self.send_push(frame)

    def push_data(self, data: FrameData):
        frame = self.new_frame()
        frame["index"] = self.index
        frame["attachments"][0] = filter_none(data.__dict__)
        self.index += 1
        self.send_push(frame)

    def new_frame(self) -> Dict:
        data = {"stack": f"{self.user}/{self.stack}",
                "token": self.token,
                "id": self.id,
                "timestamp": self.timestamp,
                "type": self.handler.media_type(),
                "client": "dstack-py",
                "version": __version__,
                "os": get_os_info()}

        if not isinstance(self.encryption_method, NoEncryption):
            data["encryption"] = self.encryption_method.info()

        return data

    def send_access(self):
        req = {"stack": f"{self.user}/{self.stack}", "token": self.token}
        self.protocol.send("/stacks/access", req)

    def send_push(self, frame: Dict) -> str:
        res = self.protocol.send("/stacks/push", frame)
        return res["url"]


def filter_none(d):
    if isinstance(d, Dict):
        return {k: filter_none(v) for k, v in d.items() if v is not None}
    return d


def get_os_info() -> Dict:
    info = uname()
    return {"sysname": info[0], "release": info[2], "version": info[3], "machine": info[4]}
