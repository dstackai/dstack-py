import io
from typing import Dict, Optional

from dstack.stack import Handler, FrameData


class MatplotlibHandler(Handler):
    """Handler to deal with matplotlib charts."""

    def to_frame_data(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Converts matplotlib figure to frame data.

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
        return FrameData(buf, description, params)

    def media_type(self) -> str:
        return self.IMAGE_SVG
