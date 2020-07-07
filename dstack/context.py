import re
from abc import ABC
from typing import Optional

from dstack.config import Profile
from dstack.protocol import Protocol


class Context(object):
    def __init__(self, stack: str, profile: Profile, protocol: Protocol):
        self.stack = stack
        self.profile = profile
        self.protocol = protocol

    def stack_path(self) -> str:
        if re.match("^[a-zA-Z0-9-_/]{3,255}$", self.stack):
            return self.stack[1:] if self.stack[0] == "/" else f"{self.profile.user}/{self.stack}"
        else:
            raise ValueError("Stack name can contain only latin letters, digits, slash and underscore")


class ContextAwareObject(ABC):
    def __init__(self, context: Optional[Context] = None):
        self._context = context

    def set_context(self, context: Context):
        self._context = context

    def get_context(self) -> Context:
        assert self._context is not None
        return self._context

