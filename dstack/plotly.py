from io import BytesIO
from typing import Dict, Optional

from plotly import __version__ as plotly_version

from dstack.stack import Handler, FrameData


class PlotlyHandler(Handler):
    def __init__(self, plotly_js_version: Optional[str] = None):
        self.plotly_js_version = plotly_js_version

    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        json = obj.to_json()
        return FrameData(BytesIO(json.encode("utf-8")), description, params,
                         {"plotly_version": plotly_version, "plotly_js_version": self.plotly_js_version})

    def media_type(self) -> str:
        return self.PLOTLY
