from csv import QUOTE_ALL
from io import StringIO
from typing import Optional, Dict

from pandas import __version__ as pandas_version, DataFrame, read_csv

from dstack import BytesContent
from dstack.content import MediaType
from dstack.handler import Encoder, Decoder
from dstack.stack import FrameData


class DataFrameEncoder(Encoder[DataFrame]):
    def __init__(self, encoding: str = "utf-8", header: bool = True,
                 index: bool = False):
        self.encoding = encoding
        self.header = header
        self.index = index

    def encode(self, obj: DataFrame, description: Optional[str], params: Optional[Dict]) -> FrameData:
        buf = StringIO()
        schema = [str(t) for t in obj.dtypes]
        obj.to_csv(buf, index=self.index, header=self.header, encoding=self.encoding, quoting=QUOTE_ALL)
        return FrameData(BytesContent(buf.getvalue().encode(self.encoding)), MediaType("text/csv", "pandas/dataframe"),
                         description, params,
                         {"header": self.header,
                          "index": self.index,
                          "schema": schema,
                          "encoding": self.encoding,
                          "version": pandas_version})


class DataFrameDecoder(Decoder[DataFrame]):

    def decode(self, data: FrameData) -> DataFrame:
        index_col = 0 if data.settings["index"] else None
        df = read_csv(data.data.stream(), encoding=data.settings.get("encoding", "utf-8"), index_col=index_col)

        schema = data.settings["schema"]
        cols = [str(col) for col in df.columns]

        return df.astype(dict(zip(cols, schema)))
