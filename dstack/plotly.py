from io import BytesIO
from typing import Dict, Optional

from plotly import __version__ as plotly_version

from dstack.stack import Handler, FrameData


class PlotlyHandler(Handler):
    """A class to handle Plotly charts.

    Notes:
        Handler stores Plotly version in settings part of the frame data.
    """

    def __init__(self, plotly_js_version: Optional[str] = None):
        """Create an instance with specified Plotly.js version if needed.

        Args:
            plotly_js_version: Plotly.js version to use. It will stored in the settings
            part of frame data.
        """
        self.plotly_js_version = plotly_js_version

    def to_frame_data(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Build frame data object from Plotly figure.

        Args:
            obj (plotly.graph_objs._figure.Figure): Plotly figure to publish.
            description: Description of Plotly chart.
            params: Parameters of the chart.

        Returns:
            Frame data.
        """
        json = obj.to_json()
        return FrameData(BytesIO(json.encode("utf-8")), description, params,
                         {"plotly_version": plotly_version, "plotly_js_version": self.plotly_js_version})

    def media_type(self) -> str:
        return "plotly"
