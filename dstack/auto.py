import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from dstack.stack import Handler, FrameData


class UnsupportedObjectTypeException(Exception):
    """To deal with unknown object types."""

    def __init__(self, obj):
        self.obj = obj


class AutoHandler(Handler):
    """A handler which selects appropriate implementation depending on `obj` itself in runtime."""

    def __init__(self):
        self.chain = [
            MatplotlibHandlerFactory(),
            PlotlyHandlerFactory(),
            BokehHandlerFactory(),
            PandasHandlerFactory(),
            SklearnModelHandlerFactory()]

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
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
        handler = None

        for factory in self.chain:
            if re.match(factory.class_pattern(), tpe):
                handler = factory.create_handler()

        if handler is None:
            raise UnsupportedObjectTypeException(obj)

        return handler.encode(obj, description, params)

    def decode(self, data: FrameData) -> Any:
        handler = None

        for factory in self.chain:
            media_type_pattern = factory.media_pattern()
            if media_type_pattern and re.match(media_type_pattern, data.type):
                handler = factory.create_handler()

        if handler is None:
            raise UnsupportedObjectTypeException(data.type)

        return handler.decode(data)


class HandlerFactory(ABC):
    @abstractmethod
    def class_pattern(self) -> str:
        pass

    def media_pattern(self) -> Optional[str]:
        return None

    @abstractmethod
    def create_handler(self) -> Handler:
        pass


class MatplotlibHandlerFactory(HandlerFactory):

    def class_pattern(self) -> str:
        return "<class 'matplotlib.figure.Figure'>"

    def create_handler(self) -> Handler:
        from dstack.matplotlib import MatplotlibHandler
        return MatplotlibHandler()


class PlotlyHandlerFactory(HandlerFactory):

    def class_pattern(self) -> str:
        return "<class 'plotly.graph_objs._figure.Figure'>"

    def create_handler(self) -> Handler:
        from dstack.plotly import PlotlyHandler
        return PlotlyHandler()


class BokehHandlerFactory(HandlerFactory):

    def class_pattern(self) -> str:
        return "<class 'bokeh.plotting.figure.Figure'>"

    def create_handler(self) -> Handler:
        from dstack.bokeh import BokehHandler
        return BokehHandler()


class PandasHandlerFactory(HandlerFactory):

    def class_pattern(self) -> str:
        return "<class 'pandas.core.frame.DataFrame'>"

    def media_pattern(self) -> Optional[str]:
        return "text/csv"

    def create_handler(self) -> Handler:
        from dstack.pandas import DataFrameHandler
        return DataFrameHandler()


class SklearnModelHandlerFactory(HandlerFactory):

    def class_pattern(self) -> str:
        return r"<class 'sklearn\..*'>"

    def media_pattern(self) -> Optional[str]:
        return r"sklearn/.*"

    def create_handler(self) -> Handler:
        from dstack.sklearn import SklearnModelHandler
        return SklearnModelHandler()
