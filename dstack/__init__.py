from typing import Optional

from dstack.auto import AutoHandler
from dstack.config import Config, from_yaml_file
from dstack.protocol import Protocol, JsonProtocol
from dstack.stack import Handler, EncryptionMethod, NoEncryption, StackFrame


def create_frame(stack: str,
                 handler: Handler = AutoHandler(),
                 profile: str = "default",
                 auto_push: bool = False,
                 protocol: Protocol = JsonProtocol("https://api.dstack.ai"),
                 config: Optional[Config] = None,
                 encryption: EncryptionMethod = NoEncryption()) -> StackFrame:
    if config is None:
        config = from_yaml_file()
    frame = StackFrame(stack, config.get_profile(profile).token, handler, auto_push, protocol, encryption)
    frame.send_access()
    return frame