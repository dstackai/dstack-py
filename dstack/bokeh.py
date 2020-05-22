from json import dumps
from typing import Optional, Dict

from bokeh import __version__ as bokeh_version
from bokeh.embed import json_item

from dstack import BytesContent
from dstack.stack import Handler, FrameData


class BokehHandler(Handler):
    """Bokeh visualization handler.
    Notes:
        In the settings section it stores Bokeh library version as `bokeh_version`.
    """

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Convert Bokeh figure to frame data.

        Args:
            obj (bokeh.plotting.figure.Figure): Bokeh figure to publish.
            description: Bokeh plot description.
            params: Bokeh plot parameters.

        Returns:
            Frame data.
        """
        text = dumps(json_item(obj))
        return FrameData(BytesContent(text.encode("utf-8")), "bokeh", description, params, {"bokeh_version": bokeh_version})
