import base64
import json
from io import StringIO
from typing import Optional, Dict, Union
from urllib import request

from dstack.auto import AutoHandler
from dstack.config import Config, ConfigFactory, YamlConfigFactory, from_yaml_file, ConfigurationException
from dstack.protocol import Protocol, JsonProtocol
from dstack.stack import Handler, EncryptionMethod, NoEncryption, StackFrame

__config_factory: ConfigFactory = YamlConfigFactory()


def configure(config: Union[Config, ConfigFactory]):
    global __config_factory
    if isinstance(config, Config):
        class SimpleConfigFactory(ConfigFactory):
            def get_config(self) -> Config:
                return config

        __config_factory = SimpleConfigFactory()
    elif isinstance(config, ConfigFactory):
        __config_factory = config
    else:
        raise TypeError(f"Config or ConfigFactory expected but found {type(config)}")


def create_frame(stack: str,
                 handler: Handler = AutoHandler(),
                 profile: str = "default",
                 auto_push: bool = False,
                 check_access: bool = True) -> StackFrame:
    """Create a new stack frame. The method also checks access to specified stack.

    Args:
        stack: A stack you want to use. It must be a full path to the stack e.g. `project/sub-project/plot`.
        handler: A handler which can be specified in the case of custom content,
            but by default it is AutoHandler.
        profile: A profile refers to credentials, i.e. username and token. Default profile is named 'default'.
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
    config = __config_factory.get_config()
    profile = config.get_profile(profile)

    frame = StackFrame(stack=stack,
                       user=profile.user,
                       token=profile.token,
                       handler=handler,
                       auto_push=auto_push,
                       protocol=config.create_protocol(profile),
                       encryption=config.get_encryption(profile))
    if check_access:
        frame.send_access()

    return frame


def push_frame(stack: str, obj, description: Optional[str] = None,
               params: Optional[Dict] = None,
               handler: Handler = AutoHandler(),
               profile: str = "default") -> str:
    """Create frame in the stack, commits and pushes data in a single operation.

    Args:
        stack: A stack you want to commit and push to.
        obj: Object to commit and push, e.g. plot.
        description: Optional description of the object.
        params: Optional parameters.
        handler: Specify handler to handle the object, by default `AutoHandler` will be used.
        profile: Profile you want to use, i.e. username and token. Default profile is 'default'.
    Raises:
        ServerException: If server returns something except HTTP 200, e.g. in the case of authorization failure.
        ConfigurationException: If something goes wrong with configuration process, config file does not exist an so on.
    """
    frame = create_frame(stack=stack,
                         handler=handler,
                         profile=profile,
                         check_access=False)
    frame.commit(obj, description, params)
    return frame.push()


class MatchException(ValueError):
    def __init__(self, params: Dict):
        self.params = params

    def __str__(self):
        return f"Can't match parameters {self.params}"


def pull(stack: str,
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

    def do_get(url: str):
        req = request.Request(url, method="GET")
        req.add_header("Content-Type", f"application/json; charset=UTF-8")
        req.add_header("Authorization", f"Bearer {profile.token}")
        r = request.urlopen(req)
        return json.loads(r.read(), encoding="UTF-8")

    config = __config_factory.get_config()
    profile = config.get_profile(profile)
    params = {} if params is None else params.copy()
    params.update(kwargs)
    stack_path = stack if stack.startswith("/") else f"{profile.user}/{stack}"
    url = f"{profile.server}/stacks/{stack_path}"
    res = do_get(url)
    attachments = res["stack"]["head"]["attachments"]
    for index, attach in enumerate(attachments):
        if set(attach["params"].items()) == set(params.items()):
            frame = res["stack"]["head"]["id"]
            attach_url = f"{profile.server}/attachs/{stack_path}/{frame}/{index}?download=true"
            r = do_get(attach_url)
            if "data" not in r["attachment"]:
                download_url = r["attachment"]["download_url"]
                if filename is not None:
                    request.urlretrieve(download_url, filename)
                    return filename
                else:
                    return download_url
            else:
                if filename is not None:
                    f = open(filename, "wb")
                    f.write(base64.b64decode(r["attachment"]["data"]))
                    f.close()
                    return filename
                else:
                    data = base64.b64decode(r["attachment"]["data"])
                    return StringIO(data.decode("utf-8"))
    raise MatchException(params)
