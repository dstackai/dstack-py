from typing import Optional, Dict

from dstack.stack import Handler, FrameData


class UnsupportedObjectTypeException(Exception):
    def __init__(self, obj):
        self.obj = obj


class AutoHandler(Handler):
    def __init__(self):
        self.handler = None

    def as_frame(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        tpe = str(type(obj))
        if tpe == "<class 'matplotlib.figure.Figure'>":
            from dstack.matplotlib import MatplotlibHandler
            self.handler = MatplotlibHandler()
        elif tpe == "<class 'plotly.graph_objs._figure.Figure'>":
            from dstack.plotly import PlotlyHandler
            self.handler = PlotlyHandler()
        elif tpe == "<class 'bokeh.plotting.figure.Figure'>":
            from dstack.bokeh import BokehHandler
            self.handler = BokehHandler()
        else:
            raise UnsupportedObjectTypeException(obj)
        return self.handler.as_frame(obj, description, params)

    def media_type(self) -> str:
        return self.handler.media_type()
