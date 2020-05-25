import io
import sys
from typing import Optional, Dict, Any

import torch
import torch.version

from dstack import Handler, FrameData, BytesContent


class TorchModelHandler(Handler):
    STORE_STATE_DICT: bool = False
    MAP_LOCATION = None

    def __init__(self, store_state_dict=None, map_location=None):
        self.store_state_dict = store_state_dict if store_state_dict else self.STORE_STATE_DICT
        self.map_location = map_location if map_location else self.MAP_LOCATION

    def encode(self, obj, description: Optional[str], params: Optional[Dict]) -> FrameData:
        buf = io.BytesIO()

        # FIXME: add model summary here
        settings = {"class": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                    "python": sys.version,
                    "torch": torch.version.__version__}

        if self.store_state_dict:
            torch.save(obj.state_dict(), buf)
            media_type = "torch/state"
        else:
            torch.save(obj, buf)
            media_type = "torch/model"

        return FrameData(BytesContent(buf), media_type, description, params, settings)

    def decode(self, data: FrameData) -> Any:
        return torch.load(data.data.stream(), self.map_location)
