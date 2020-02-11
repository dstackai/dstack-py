from io import BytesIO
from json import dumps
from typing import Optional, Dict

from bokeh import __version__ as bokeh_version
from bokeh.embed import json_item

from dstack.stack import Handler, FrameData


class BokehHandler(Handler):
    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        text = dumps(json_item(obj))
        return FrameData(BytesIO(text.encode("utf-8")), description, params, {"bokeh_version": bokeh_version})

    def media_type(self) -> str:
        return self.BOKEH
