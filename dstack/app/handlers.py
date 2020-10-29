from typing import Callable, Optional, Dict, List

from dstack import Encoder, FrameData
from dstack.app import _undress


class AppEncoder(Encoder[Callable]):

    def encode(self, obj: Callable, description: Optional[str], params: Optional[Dict]) -> FrameData:
        obj = _undress(obj)
        self._check_signature(obj, list(params.keys()))
        # deps = _collect_deps(obj)

        pass

    @staticmethod
    def _check_signature(func: Callable, keys: List[str]):
        pass
