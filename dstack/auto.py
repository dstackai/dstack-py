import inspect
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from dstack.handler import Handler, FrameData


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
            SklearnModelHandlerFactory(),
            TorchModelHandlerFactory()]

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
        return self.find_handler(obj).encode(obj, description, params)

    def decode(self, data: FrameData) -> Any:
        return self.find_handler(data.type).decode(data)

    def find_handler(self, obj):
        for factory in self.chain:
            if factory.accept(obj):
                return factory.create_handler()

        raise UnsupportedObjectTypeException(obj)




class HandlerFactory(ABC):
    @abstractmethod
    def accept(self, obj: Any) -> bool:
        pass

    @abstractmethod
    def create_handler(self) -> Handler:
        pass

    @staticmethod
    def has_type(obj: Any, tpe: str) -> bool:
        return f"<class '{tpe}'>" in map(lambda x: str(x), inspect.getmro(obj.__class__))

    @staticmethod
    def is_type(obj: Any, tpe: str) -> bool:
        return str(type(obj)) == f"<class '{tpe}'>"

    @staticmethod
    def is_media(obj: Any, media: List[str]):
        return isinstance(obj, str) and str(obj) in media


class MatplotlibHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_type(obj, "matplotlib.figure.Figure")

    def create_handler(self) -> Handler:
        from dstack.matplotlib import MatplotlibHandler
        return MatplotlibHandler()


class PlotlyHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_type(obj, "plotly.graph_objs._figure.Figure")

    def create_handler(self) -> Handler:
        from dstack.plotly import PlotlyHandler
        return PlotlyHandler()


class BokehHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_type(obj, "bokeh.plotting.figure.Figure")

    def create_handler(self) -> Handler:
        from dstack.bokeh import BokehHandler
        return BokehHandler()


class PandasHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_media(obj, ["text/csv"]) or \
               self.is_type(obj, "pandas.core.frame.DataFrame")

    def create_handler(self) -> Handler:
        from dstack.pandas import DataFrameHandler
        return DataFrameHandler()


class SklearnModelHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_media(obj, ["sklearn/pickle", "sklearn/joblib"]) or \
               self.has_type(obj, "sklearn.base.BaseEstimator")

    def create_handler(self) -> Handler:
        from dstack.sklearn import SklearnModelHandler
        return SklearnModelHandler()


class TorchModelHandlerFactory(HandlerFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_media(obj, ["torch/state", "torch/model"]) or \
               self.has_type(obj, "torch.nn.modules.module.Module")

    def create_handler(self) -> Handler:
        from dstack.torch import TorchModelHandler
        return TorchModelHandler()
