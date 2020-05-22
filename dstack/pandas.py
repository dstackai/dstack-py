from csv import QUOTE_ALL
from io import StringIO
from typing import Optional, Dict

from pandas import __version__ as pandas_version

from dstack import Handler, BytesContent
from dstack.stack import FrameData


class DataFrameHandler(Handler):
    def __init__(self, encoding: str = "utf-8", header: bool = True,
                 index: bool = False):
        self.encoding = encoding
        self.header = header
        self.index = index

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        buf = StringIO()
        schema = [str(t) for t in obj.dtypes]
        obj.to_csv(buf, index=self.index, header=self.header, encoding=self.encoding, quoting=QUOTE_ALL)
        return FrameData(BytesContent(buf.getvalue().encode(self.encoding)), "text/csv", description, params,
                         {"header": self.header, "index": self.index,
                          "schema": schema, "source": "pandas",
                          "version": pandas_version})
