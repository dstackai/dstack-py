import io

from typing import Dict, Optional
from dstack.stack import Handler, FrameData


class MatplotlibHandler(Handler):
    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        buf = io.BytesIO()
        obj.savefig(buf, format="svg")
        return FrameData(buf, description, params)

    def media_type(self) -> str:
        return self.IMAGE_SVG
