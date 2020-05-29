import io
from typing import Dict, Optional

from dstack import BytesContent
from dstack.content import MediaType
from dstack.stack import Handler, FrameData


class MatplotlibHandler(Handler):
    """Handler to deal with matplotlib charts."""

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Convert matplotlib figure to frame data.

        Notes:
            Figure will be converted to SVG format.

        Args:
            obj (matplotlib.figure.Figure): Plot to be published.
            description: Description of the plot.
            params: Plot parameters if specified.

        Returns:
            Corresponding `FrameData` object.
        """
        buf = io.BytesIO()
        obj.savefig(buf, format="svg")
        return FrameData(BytesContent(buf), MediaType("image/svg+xml", "matplotlib"), description, params)
