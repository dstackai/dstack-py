from typing import Optional, Dict

from dstack.stack import Handler, FrameData


class UnsupportedObjectTypeException(Exception):
    """To deal with unknown object types."""

    def __init__(self, obj):
        self.obj = obj


class AutoHandler(Handler):
    """A handler which selects appropriate implementation depending on `obj` itself in runtime."""

    def __init__(self):
        self.chain = {
            "<class 'matplotlib.figure.Figure'>": matplotlib_factory,
            "<class 'plotly.graph_objs._figure.Figure'>": plotly_factory,
            "<class 'bokeh.plotting.figure.Figure'>": bokeh_factory,
            "<class 'pandas.core.frame.DataFrame'>": pandas_factory
        }

    def to_frame_data(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        """Create frame data from any known object.

        Args:
            obj: An object.
            description: Object description.
            params: Object parameters.

        Returns:
            Frame data.

        Raises:
            UnsupportedObjectTypeException: In the case of unknown object type.
        """
        tpe = str(type(obj))
        if tpe in self.chain:
            handler = self.chain[tpe]()
        else:
            raise UnsupportedObjectTypeException(obj)
        return handler.to_frame_data(obj, description, params)


def matplotlib_factory() -> Handler:
    from dstack.matplotlib import MatplotlibHandler
    return MatplotlibHandler()


def plotly_factory() -> Handler:
    from dstack.plotly import PlotlyHandler
    return PlotlyHandler()


def bokeh_factory() -> Handler:
    from dstack.bokeh import BokehHandler
    return BokehHandler()


def pandas_factory() -> Handler:
    from dstack.pandas import DataFrameHandler
    return DataFrameHandler()
