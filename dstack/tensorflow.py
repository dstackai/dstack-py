import sys
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Dict, Any
from uuid import uuid4

import tensorflow as tf
from tensorflow import keras

from dstack import Handler, FrameData
from dstack.content import FileContent, MediaType


class TensorFlowKerasModelHandler(Handler):
    STORE_WHOLE_MODEL: bool = True

    def __init__(self, store_whole_model: Optional[bool] = None,
                 save_format: str = "tf", tmp_dir: Optional[str] = None):
        self.store_whole_model = store_whole_model if store_whole_model else self.STORE_WHOLE_MODEL
        self.tmp_dir = Path(tmp_dir if tmp_dir else gettempdir())
        self.save_format = save_format

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        filename = self.tmp_dir / Path(str(uuid4()))

        if self.store_whole_model:
            obj.save(filename, save_format=self.save_format)
            application_type = "tensorflow/model"
        else:
            obj.save_wights(filename, save_format=self.save_format)
            application_type = "tensorflow/weights"

        settings = {
            "class": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            "python": sys.version,
            "tensorflow": tf.__version__
        }

        return FrameData(FileContent(filename),
                         MediaType("application/binary", application_type, self.save_format),
                         description, params, settings)

    def decode(self, data: FrameData) -> Any:
        filename = self.tmp_dir / Path(f"{str(uuid4())}.{data.storage_format}")
        return keras.models.load_model(filename)
