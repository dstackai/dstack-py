from pathlib import Path
from typing import Optional, Dict

from dstack import Encoder, FrameData, StreamContent, MediaType
from dstack.content import CONTENT_TYPE_MAP_REVERSED


class FileEncoder(Encoder[Path]):
    def encode(self, obj: Path, description: Optional[str], params: Optional[Dict]) -> FrameData:
        length = obj.stat().st_size
        ext = obj.suffix[1:]
        media_type = MediaType(CONTENT_TYPE_MAP_REVERSED.get(ext, "application/binary"))
        f = obj.open("rb")
        buf = StreamContent(f, length)
        return FrameData(buf, media_type, description, params, {"filename": obj.name})

