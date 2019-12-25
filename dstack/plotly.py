from io import BytesIO
from typing import Dict, Optional
from plotly.offline import plot
from dstack.stack import Handler, FrameData


class PlotlyHandler(Handler):
    def __init__(self, plotly_js_version: str = "latest"):
        self.plotly_js_version = plotly_js_version

    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        div = plot(obj, include_plotlyjs=False, output_type="div")
        libs = ["https://cdn.plot.ly/plotly-%s.min.js" % self.plotly_js_version]
        return FrameData(BytesIO(div.encode("utf-8")), description, params, libs)

    def media_type(self) -> str:
        return self.TEXT_HTML
