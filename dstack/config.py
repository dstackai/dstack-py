from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict

import yaml

API_SERVER = "https://api.dstack.ai"


class ConfigurationException(Exception):
    def __init__(self, message):
        self.message = message


class Profile(object):
    """To manage tokens CLI tools are used, so sensitive information like token and server is stored separately
    in configuration files. Every configuration file contains profiles section which stores all profiles the user
    have configured.

    Attributes:
         name (str): A name of the profile which can be used in code to identify token and server.
         user (str): Username.
         token (str):  A token of selected profile.
         server (str): API endpoint.
    """

    def __init__(self, name: str, user: str, token: str, server: str):
        """Create a profile object.

        Args:
            name (str): Profile name.
            user (str): Username.
            token (str): A token which will be used with this profile.
            server (str): A server which provides API calls.
        """
        self.name = name
        self.user = user
        self.token = token
        self.server = server


class Config(ABC):
    """An abstract class for configuration. It is needed to access and manage to profiles.
    By default system will use `YamlConfig` which works with YAML files located in working and home directories,
    but in some cases may be useful to store profiles in database or somewhere. To do so one have to inherit this class
    and override certain methods in the proper way.
    """

    @abstractmethod
    def list_profiles(self) -> Dict[str, Profile]:
        """Return a map of profiles, where keys are profile names, values are `Profile` objects.

        Returns:
            A dictionary of available profiles. If there is no configured profiles empty dictionary will be returned.
        """
        pass

    @abstractmethod
    def get_profile(self, name: str) -> Optional[Profile]:
        """Get profile by name.

        Args:
            name (str): A name of profile you are looking for.

        Returns:
            A profile if it exists otherwise `None`.
        """
        pass

    @abstractmethod
    def add_or_replace_profile(self, profile: Profile):
        """Add or replace existing profile in the configuration. This operation doesn't persist anything, just changes.
        To persist configuration use `save` method.

        Args:
            profile (Profile): Profile to change. All data related to profile with same name will be replaced.
        """
        pass

    @abstractmethod
    def save(self):
        """Save configuration."""
        pass

    @abstractmethod
    def remove_profile(self, name: str) -> Profile:
        """Delete specified profile.

        Args:
            name (str): A name of the profile to delete.

        Returns:
            Deleted profile.
        """
        pass


class YamlConfig(Config):
    """A class implements `Config` contracts for YAML format stored on disk. This implementation relies on PyYAML package.
    Comments can't be used in config file, because `save` method will remove it all. So, editing of configuration files
    is not recommended. To configure please use dstack CLI tools.

    See Also:
        `from_yaml_file`
    """

    def __init__(self, yaml_data, path: Path):
        """Create an instance from loaded data.

        Args:
            yaml_data: Dictionary like structure to store configuration.
            path: Filename on disk to save changes.
        """
        super().__init__()
        self.yaml_data = yaml_data
        self.path = path

    def list_profiles(self) -> Dict[str, Profile]:
        result = {}
        profiles = self.yaml_data.get("profiles", {})
        for k in profiles.keys():
            result[k] = self.get_profile(k)
        return result

    def get_profile(self, name: str) -> Optional[Profile]:
        """Return profile with specified name or `None`.

        Notes:
            In the case if server is not configured standard endpoint will be used.

        Args:
            name (str): A name of profile.

        Returns:
            Profile if it exists, otherwise `None`.
        """
        profiles = self.yaml_data.get("profiles", {})
        profile = profiles.get(name, None)
        if profile is None:
            return None
        else:
            return Profile(name, profile["user"], profile["token"], profile.get("server", API_SERVER))

    def add_or_replace_profile(self, profile: Profile):
        """Add or replaces existing profile.

        Notes:
            If server information refers to standard endpoint there will be no `server` key at all.
            Which coincides with `get_profile` behaviour.
        Args:
            profile: Profile to add or replace.
        """
        profiles = self.yaml_data.get("profiles", {})
        update = {"token": profile.token, "user": profile.user}
        if profile.server != API_SERVER:
            update["server"] = profile.server
        profiles[profile.name] = update
        self.yaml_data["profiles"] = profiles

    def save(self):
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)
        content = yaml.dump(self.yaml_data)
        self.path.write_text(content, encoding="utf-8")

    def remove_profile(self, name: str) -> Profile:
        profiles = self.yaml_data
        profile = profiles[name]
        del profiles[name]
        return profile

    def __repr__(self) -> str:
        return str(self.yaml_data)


def from_yaml_file(use_global_settings: Optional[bool] = None,
                   dstack_dir: str = ".dstack", error_if_not_exist: bool = False) -> Config:
    """Load YAML configuration.

    Args:
        use_global_settings: Force to use global settings (located in home directory).
            If it's not set algorithm tries to find settings locally, if it fails it looks up in home directory.
            In the case than it's `True` it uses global settings otherwise local ones.
        dstack_dir: A directory where all dstack stuff is stored, buy default is `.dstack`.
        error_if_not_exist: Force to produce error in the case of the file does not exist, by default it is `False`.
    Returns:
        YAML based configuration.

    Raises:
        ConfigurationException: If `error_if_not_exist` is `True` and file does not exist.
    """
    path = local_path = Path(dstack_dir) / Path("config.yaml")

    if use_global_settings or (use_global_settings is None and not path.exists()):
        path = Path.home() / path

    if not path.exists():
        if error_if_not_exist:
            raise ConfigurationException(f"Configuration file does not exist, type `dstack config` in command line")
        else:
            return YamlConfig({}, path if use_global_settings else local_path)

    with path.open() as f:
        return YamlConfig(yaml.load(f, Loader=yaml.FullLoader), path)
