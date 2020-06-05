from typing import Any

from dstack.content import MediaType
from dstack.handler import Encoder, Decoder, EncoderFactory, DecoderFactory


class DataFrameEncoderFactory(EncoderFactory):

    def accept(self, obj: Any) -> bool:
        return self.is_type(obj, "pandas.core.frame.DataFrame")

    def create(self) -> Encoder:
        from dstack.pandas.handlers import DataFrameEncoder
        return DataFrameEncoder()


class DataFrameDecoderFactory(DecoderFactory):

    def accept(self, obj: MediaType) -> bool:
        return obj.application == "pandas/dataframe"

    def create(self) -> Decoder:
        from dstack.pandas.handlers import DataFrameDecoder
        return DataFrameDecoder()
