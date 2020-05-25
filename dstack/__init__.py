import base64
from io import StringIO
from typing import Optional, Dict, Union, Any

from dstack.auto import AutoHandler
from dstack.config import Config, ConfigFactory, YamlConfigFactory, \
    from_yaml_file, ConfigurationException, get_config, Profile
from dstack.content import StreamContent, BytesContent
from dstack.protocol import Protocol, JsonProtocol, MatchException, create_protocol
from dstack.stack import Handler, EncryptionMethod, NoEncryption, StackFrame, stack_path, merge_or_none, FrameData


def push_frame(stack: str, obj, description: Optional[str] = None,
               message: Optional[str] = None,
               params: Optional[Dict] = None,
               handler: Handler = AutoHandler(),
               profile: str = "default",
               **kwargs) -> str:
    """Create frame in the stack, commits and pushes data in a single operation.

    Args:
        stack: A stack you want to commit and push to.
        obj: Object to commit and push, e.g. plot.
        description: Optional description of the object.
        message: Push message to describe what's new in this revision.
        params: Optional parameters.
        handler: Specify a handler to handle the object, by default `AutoHandler` will be used.
        profile: Profile you want to use, i.e. username and token. Default profile is 'default'.
        **kwargs: Optional parameters is an alternative to params. If both are present this one
            will be merged into params.
    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    frame = create_frame(stack=stack,
                         profile=profile,
                         check_access=False)
    frame.commit(obj, description, params, handler, **kwargs)
    return frame.push(message)


def create_frame(stack: str,
                 profile: str = "default",
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
        auto_push:  Tells the system to push frame just after commit. It may be useful if you
            want to see result immediately. Default is False.
        check_access: Check access to be sure about credentials before trying to actually push something.
            Default is `True`.

    Returns:
        A new stack frame.

    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    profile = get_config().get_profile(profile)

    frame = StackFrame(stack=stack,
                       user=profile.user,
                       token=profile.token,
                       auto_push=auto_push,
                       protocol=create_protocol(profile),
                       encryption=get_encryption(profile))
    if check_access:
        frame.send_access()

    return frame


def pull1(stack: str,
          profile: str = "default",
          filename: Optional[str] = None,
          params: Optional[Dict] = None, **kwargs) -> Union[str, StringIO]:
    """Pull data object from stack frame (head) which matches specified parameters.

    Args:
        stack: Stack you want to pull from.
        profile: Profile to use. 'default' will be used if profile is not specified.
        filename: Filename if you want to store downloaded file on disk.
        params: Parameters to match. In can be used in the case if parameter has a name with spaces, otherwise use **kwargs instead.
            If both are used actual parameters to match will be **kwargs merged to params.
        **kwargs: Parameters to match.

    Returns:
        StringIO object in the case of small files, URL if file is large.

    Raises:
        MatchException if there is no object that matches the parameters.
    """
    d = pull_raw(stack, profile, params, **kwargs)
    if filename is not None:
        with open(filename, "wb") as f:
            f.write(d.data.value())
        return filename
    else:
        return StringIO(d.data.value().decode("utf-8"))


def get_encryption(profile: Profile) -> EncryptionMethod:
    return NoEncryption()


def pull_raw(stack: str,
             profile: str = "default",
             params: Optional[Dict] = None, **kwargs) -> FrameData:
    profile = get_config().get_profile(profile)
    protocol = create_protocol(profile)
    params = merge_or_none(params, kwargs)
    path = stack_path(profile.user, stack)
    res = protocol.pull(path, profile.token, params)
    attach = res["attachment"]

    data = \
        BytesContent(base64.b64decode(attach["data"])) if "data" in attach else \
            StreamContent(*protocol.download(attach["download_url"]))

    return FrameData(data, attach["type"], attach["description"], params, attach.get("settings", None))


def pull(stack: str,
         profile: str = "default",
         params: Optional[Dict] = None, **kwargs) -> Any:
    return AutoHandler().decode(pull_raw(stack, profile, params, **kwargs))
