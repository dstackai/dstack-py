import base64
from typing import Optional, Dict, Any

from deprecation import deprecated

from dstack.auto import AutoHandler
from dstack.config import Config, ConfigFactory, YamlConfigFactory, \
    from_yaml_file, ConfigurationError, get_config, Profile
from dstack.content import StreamContent, BytesContent, MediaType
from dstack.context import Context
from dstack.handler import Encoder, Decoder, T, DecoratedValue
from dstack.protocol import Protocol, JsonProtocol, MatchError, create_protocol
from dstack.stack import EncryptionMethod, NoEncryption, StackFrame, merge_or_none, FrameData, PushResult, FrameParams


def push(stack: str, obj, description: Optional[str] = None,
         access: Optional[str] = None,
         frame_params: Optional[FrameParams] = None,
         params: Optional[Dict] = None,
         encoder: Optional[Encoder[Any]] = None,
         profile: str = "default",
         **kwargs) -> PushResult:
    """Create a frame in the stack, commits and pushes data in a single operation.

    Args:
        stack: A stack you want to commit and push to.
        obj: Object to commit and push, e.g. plot.
        description: Optional description of the object.
        access: Access level for the stack. It may be public, private or None. It is None by default, so it will be
                default access level in user's settings.
        frame_params: Push message to associate some parameters with this revision, e.g. text message.
        params: Optional parameters.
        encoder: Specify a handler to handle the object, by default `AutoHandler` will be used.
        profile: Profile you want to use, i.e. username and token. Default profile is 'default'.
        **kwargs: Revision parameters.
    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """

    f = frame(stack=stack,
              profile=profile,
              access=access,
              check_access=False)
    f.add(obj, description, params, encoder, **kwargs)
    return f.push(frame_params)


@deprecated(details="Use push instead")
def push_frame(stack: str, obj, description: Optional[str] = None,
               access: Optional[str] = None,
               message: Optional[str] = None,
               params: Optional[Dict] = None,
               encoder: Optional[Encoder[Any]] = None,
               profile: str = "default",
               **kwargs) -> PushResult:
    """Create a frame in the stack, commits and pushes data in a single operation.

    Args:
        stack: A stack you want to commit and push to.
        obj: Object to commit and push, e.g. plot.
        description: Optional description of the object.
        access: Access level for the stack. It may be public, private or None. It is None by default, so it will be
                default access level in user's settings.
        message: Push message to describe what's new in this revision.
        params: Optional parameters.
        encoder: Specify a handler to handle the object, by default `AutoHandler` will be used.
        profile: Profile you want to use, i.e. username and token. Default profile is 'default'.
        **kwargs: Optional parameters is an alternative to params. If both are present this one
            will be merged into params.
    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    return push(stack, obj, description, access, FrameParams(message=message), params, encoder, profile, **kwargs)


def frame(stack: str,
          profile: str = "default",
          access: Optional[str] = None,
          auto_push: bool = False,
          check_access: bool = True) -> StackFrame:
    """Create a new stack frame. The method also checks access to specified stack.

    Args:
        stack: A stack you want to use. It must be a full path to the stack e.g. `project/sub-project/plot`.
        profile: A profile refers to credentials, i.e. username and token. Default profile is 'default'.
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
        access: Specify access level for this stack. It may be one of the following:
            private - This means the stack will be visible only for the author.
            public  - The stack will be accessible for everyone.
            None    - Default access level will be used, one can find it in own settings on dstack server.
            If it is not specified default access level will be used.
        auto_push:  Tells the system to push frame just after the commit. It may be useful if you
            want to see result immediately. Default is False.
        check_access: Check access to be sure about credentials before trying to actually push something.
            Default is `True`.

    Returns:
        A new stack frame.

    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    if access and access not in ["private", "public"]:
        raise ValueError(f"access can be only private, public or None but found {access}")

    context = create_context(stack, profile)

    return _create_frame(context, access=access, auto_push=auto_push, check_access=check_access)


@deprecated(details="Use frame instead")
def create_frame(stack: str,
                 profile: str = "default",
                 access: Optional[str] = None,
                 auto_push: bool = False,
                 check_access: bool = True) -> StackFrame:
    """Create a new stack frame. The method also checks access to specified stack.

    Args:
        stack: A stack you want to use. It must be a full path to the stack e.g. `project/sub-project/plot`.
        profile: A profile refers to credentials, i.e. username and token. Default profile is 'default'.
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
        access: Specify access level for this stack. It may be one of the following:
            private - This means the stack will be visible only for the author.
            public  - The stack will be accessible for everyone.
            None    - Default access level will be used, one can find it in own settings on dstack server.
            If it is not specified default access level will be used.
        auto_push:  Tells the system to push frame just after the commit. It may be useful if you
            want to see result immediately. Default is False.
        check_access: Check access to be sure about credentials before trying to actually push something.
            Default is `True`.

    Returns:
        A new stack frame.

    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    return frame(stack, profile, access, auto_push, check_access)


def _create_frame(context: Context, access: Optional[str] = None, auto_push: bool = False,
                  check_access: bool = True) -> StackFrame:
    frame = StackFrame(context,
                       access=access,
                       auto_push=auto_push,
                       encryption=get_encryption(context.profile))
    if check_access:
        frame.send_access()

    return frame


# def _push(context: Context, obj: Any,
#           description: Optional[str] = None,
#           access: Optional[str] = None,
#           message: Optional[str] = None,
#           params: Optional[Dict] = None,
#           encoder: Optional[Encoder[Any]] = None,
#           **kwargs) -> PushResult:
#     frame = _create_frame(context,
#                           access=access,
#                           check_access=False)
#     frame.commit(obj, description, params, encoder, **kwargs)
#     return frame.push(message)


def get_encryption(profile: Profile) -> EncryptionMethod:
    return NoEncryption()


def pull_data(context: Context,
              params: Optional[Dict] = None, **kwargs) -> FrameData:
    path = context.stack_path()
    params = merge_or_none(params, kwargs)
    res = context.protocol.pull(path, context.profile.token, params)
    attach = res["attachment"]

    data = \
        BytesContent(base64.b64decode(attach["data"])) if "data" in attach else \
            StreamContent(*context.protocol.download(attach["download_url"]))

    media_type = MediaType(attach["content_type"], attach.get("application", None))
    return FrameData(data, media_type, attach.get("description", None),
                     attach.get("params", None), attach.get("settings", None))


def pull(stack: str,
         profile: str = "default",
         params: Optional[Dict] = None,
         decoder: Optional[Decoder[Any]] = None,
         **kwargs) -> Any:
    return _pull(create_context(stack, profile), params, decoder, **kwargs)


def _pull(context: Context,
          params: Optional[Dict] = None,
          decoder: Optional[Decoder[Any]] = None,
          **kwargs) -> Any:
    decoder = decoder or AutoHandler()
    decoder.set_context(context)
    return decoder.decode(pull_data(context, params, **kwargs))


def create_context(stack: str, profile: str = "default") -> Context:
    profile = get_config().get_profile(profile)
    protocol = create_protocol(profile)
    return Context(stack, profile, protocol)


def tab(title: Optional[str] = None) -> DecoratedValue:
    class Tab(DecoratedValue):
        def __init__(self, title: Optional[str] = None):
            self.title = title

        def decorate(self) -> Dict[str, Any]:
            decorated = {"type": "tab"}

            if self.title:
                decorated["title"] = self.title

            return decorated

    return Tab(title)
