from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from dstack.content import Content, MediaType


class FrameData:
    """Represent frame data structure which will be attached to stack frame by `commit` and can be sent by protocol
    implementation, as JSON for example. Every frame can contain many `FrameData` objects, any such object represent
    a piece of data user is going to publish, e.g. a chart with specified parameters.
    Every frame must have at least one `FrameData` object attached.
    Any handler must produce `FrameData` from raw data, like Matplotlib `Figure` or any other chart object.
    """

    def __init__(self, data: Content,
                 media_type: MediaType,
                 description: Optional[str],
                 params: Optional[Dict],
                 settings: Optional[Dict] = None):
        """Create frame data.
        Args:
            data: A binary representation of the object to be displayed.
            media_type: Supported media type.
            description: Optional description.
            params: A dictionary with parameters which will be used to produce appropriate controls.
            settings: Optional settings are usually used to store libraries versions or extra information
                required to display data correctly.
        """
        self.data = data
        self.content_type = media_type.content_type
        self.application_type = media_type.application_type
        self.storage_format = media_type.storage_format
        self.description = description
        self.params = params
        self.settings = settings


class Handler(ABC):

    @abstractmethod
    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Convert data object to appropriate format.
        Args:
            obj: A data which is needed to be converted, e.g. plot.
            description: Description of the data.
            params: Parameters of the data, which are needed to be displayed,
                e.g. plot or model settings.

        Returns:
            Frame data.
        """
        pass

    def decode(self, data: FrameData) -> Any:
        return None
