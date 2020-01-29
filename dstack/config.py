from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List
import yaml


class Profile(object):
    def __init__(self, name: str, token: str):
        self.name = name
        self.token = token


class Config(ABC):
    @abstractmethod
    def list_profiles(self) -> Dict[str, Profile]:
        pass

    @abstractmethod
    def get_profile(self, name: str) -> Optional[Profile]:
        pass

    @abstractmethod
    def add_or_replace_profile(self, profile: Profile):
        pass

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def remove_profile(self, name: str) -> Profile:
        pass


class YamlConfig(Config):
    def __init__(self, yaml_data, path: Path):
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
        profiles = self.yaml_data.get("profiles", {})
        profile = profiles.get(name, None)
        if profile is None:
            return None
        else:
            return Profile(name, profile["token"])

    def add_or_replace_profile(self, profile: Profile):
        profiles = self.yaml_data.get("profiles", {})
        profiles.update({f"{profile.name}": {"token": profile.token}})
        self.yaml_data.update({"profiles": profiles})

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


def from_yaml_file(use_global_settings: bool = False, dstack_dir: str = ".dstack") -> Config:
    path = local_path = Path(dstack_dir) / Path("config.yaml")

    if use_global_settings or not path.exists():
        path = Path.home() / path

    if not path.exists():
        return YamlConfig({}, path if use_global_settings else local_path)

    with path.open() as f:
        return YamlConfig(yaml.load(f, Loader=yaml.FullLoader), path)
