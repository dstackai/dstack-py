from typing import Optional, Dict

from dstack.auto import AutoHandler
from dstack.config import Config, from_yaml_file
from dstack.protocol import Protocol, JsonProtocol
from dstack.stack import Handler, EncryptionMethod, NoEncryption, StackFrame


def create_frame(stack: str,
                 handler: Optional[Handler] = None,
                 profile: str = "default",
                 auto_push: bool = False,
                 protocol: Optional[Protocol] = None,
                 config: Optional[Config] = None,
                 encryption: Optional[EncryptionMethod] = None) -> StackFrame:
    """Creates a new stack frame. The method also checks access to specified stack.

    Args:
        stack: A stack you want to use. It must be a full path to the stack e.g. `user/project/sub-project/plot`.
        handler: A handler which can be specified in the case of custom content,
            but by default it is AutoHandler.
        profile: A profile refers to credentials, i.e. token. Default profile is named 'default'.
            The system is looking for specified profile as follows:
            it looks into working directory to find a configuration file (local configuration),
            if the file doesn't exist it looks into user directory to find it (global configuration).
            There are CLI tools to manage profiles. You can use this command in console:

                $ dstack config --list

            to list existing profiles or add or replace token by following command:

                $ dstack config --profile <PROFILE>

            or simply

                $ dstack config

            if <PROFILE> is not specified 'default' profile will be created. The system asks you about token
            from command line, make sure that you have already obtained token from the site.
        auto_push:  Tells the system to push frame just after commit. It may be useful if you
            want to see result immediately. Default is False.
        protocol: A protocol, if None then `JsonProtocol` will be used.
        config: By default YAML-based configuration `YamlConfig` is used with file lookup
            rules described above.
        encryption: An encryption method, by default encryption is not provided,
            so it is `NoEncryption`.

    Returns:
        A new stack frame.

    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    if config is None:
        config = from_yaml_file(error_if_not_exist=True)

    if handler is None:
        handler = AutoHandler()

    if encryption is None:
        encryption = NoEncryption()

    profile = config.get_profile(profile)

    if protocol is None:
        protocol = JsonProtocol(profile.server)

    frame = StackFrame(stack=stack,
                       user=profile.user,
                       token=profile.token,
                       handler=handler,
                       auto_push=auto_push,
                       protocol=protocol,
                       encryption=encryption)
    frame.send_access()
    return frame


def push_frame(stack: str, obj, description: Optional[str] = None,
               params: Optional[Dict] = None,
               handler: Optional[Handler] = None,
               profile: str = "default",
               config: Optional[Config] = None,
               encryption: Optional[EncryptionMethod] = None) -> str:
    """Creates frame in the stack, commits and pushes data in a single operation.

    Args:
        stack: A stack you want to commit and push to.
        obj: Object to commit and push, e.g. plot.
        description: Optional description of the object.
        params: Optional parameters.
        handler: Specify handler to handle the object, if it's None then `AutoHandler` will be used.
        profile: Profile you want to use, i.e. username and token. Default profile is 'default'.
        config: Configuration to manage profiles. If it is unspecified `YamlConfig` will be used.
        encryption: Encryption method if it's `None`, `NoEncryption` will be used.
    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    frame = create_frame(stack=stack,
                         handler=handler,
                         profile=profile,
                         config=config,
                         encryption=encryption)
    frame.commit(obj, description, params)
    return frame.push()
