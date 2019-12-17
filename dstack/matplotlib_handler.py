import io

from typing import Dict

from matplotlib.figure import Figure

from dstack.stack import Handler, FrameData


class MatplotlibHandler(Handler):
    def accept(self, obj) -> bool:
        return isinstance(obj, Figure)

    def as_frame(self, obj, description: str, params: Dict) -> FrameData:
        fig: Figure = obj
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        return FrameData(buf, description, params, self.IMAGE_PNG)
