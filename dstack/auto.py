from typing import Optional, Dict, Any, List, TypeVar

from dstack.bokeh import BokehEncoderFactory
from dstack.handler import FrameData, Encoder, Decoder, AbstractFactory
from dstack.matplotlib import MatplotlibEncoderFactory
from dstack.pandas import DataFrameEncoderFactory, DataFrameDecoderFactory
from dstack.plotly import PlotlyEncoderFactory
from dstack.sklearn import SklearnModelEncoderFactory, SklearnModelDecoderFactory
from dstack.tensorflow import TensorFlowKerasModelDecoderFactory, TensorFlowKerasModelEncoderFactory
from dstack.torch import TorchModelEncoderFactory, TorchModelDecoderFactory


class UnsupportedObjectTypeException(Exception):
    """To deal with unknown object types."""

    def __init__(self, obj):
        self.obj = obj


T = TypeVar("T")
S = TypeVar("S")


class AutoHandler(Encoder[Any], Decoder[Any]):
    """A handler which selects appropriate implementation depending on `obj` itself in runtime."""

    def __init__(self):
        self.encoders = [
            MatplotlibEncoderFactory(),
            PlotlyEncoderFactory(),
            BokehEncoderFactory(),
            DataFrameEncoderFactory(),
            SklearnModelEncoderFactory(),
            TorchModelEncoderFactory(),
            TensorFlowKerasModelEncoderFactory()]

        self.decoders = [
            DataFrameDecoderFactory(),
            SklearnModelDecoderFactory(),
            TorchModelDecoderFactory(),
            TensorFlowKerasModelDecoderFactory()]

    def encode(self, obj: Any, description: Optional[str], params: Optional[Dict]) -> FrameData:
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
        return self.find_handler(obj, self.encoders).encode(obj, description, params)

    def decode(self, data: FrameData) -> Any:
        return self.find_handler(data.media_type(), self.decoders).decode(data)

    @staticmethod
    def find_handler(obj: T, chain: List[AbstractFactory[T, S]]) -> S:
        for factory in chain:
            if factory.accept(obj):
                return factory.create()

        raise UnsupportedObjectTypeException(obj)
