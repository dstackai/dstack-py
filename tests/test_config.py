from pathlib import Path
from typing import Dict
from unittest import TestCase

from yaml import dump

from dstack.config import from_yaml_file, Profile


class TestYamlConfig(TestCase):
    def setUp(self):
        self.dstack_dir = ".test_dstack"
        self.local_path = Path(self.dstack_dir)
        self.config_filename = "config.yaml"
        self.global_path = Path.home() / self.local_path
        if not self.local_path.exists():
            self.local_path.mkdir(parents=True)
        if not self.global_path.exists():
            self.global_path.mkdir(parents=True)

    def tearDown(self):
        local_config = self.local_path / self.config_filename
        global_config = self.global_path / self.config_filename
        if local_config.exists():
            local_config.unlink()
            self.local_path.rmdir()
        if global_config.exists():
            global_config.unlink()
            self.global_path.rmdir()

    def test_empty_config(self):
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        # shouldn't raise an exception
        conf.list_profiles()
        conf.add_or_replace_profile(Profile("default", "test_token"))
        conf.save()
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        self.assertEqual(1, len(conf.list_profiles()))
        self.assertEqual("test_token", conf.get_profile("default").token)

    def test_locate_config(self):
        local_conf = {"profiles": {"my_profile": {"token": "my_token"}}}
        global_conf = self.conf_example()
        self.create_yaml_file(self.global_path, global_conf)
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        # print(conf)
        self.assertEqual(2, len(conf.list_profiles()))
        self.assertEqual("token1", conf.get_profile("default").token)
        self.assertEqual("token2", conf.get_profile("other").token)

        self.create_yaml_file(self.local_path, local_conf)
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        self.assertEqual(1, len(conf.list_profiles()))
        self.assertEqual("my_token", conf.get_profile("my_profile").token)

    def test_save_and_load(self):
        self.create_yaml_file(self.local_path, self.conf_example())
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        default = conf.get_profile("default")
        profile = conf.get_profile("other")
        profile.token = "my_new_token"
        conf.add_or_replace_profile(profile)
        conf.save()
        conf = from_yaml_file(dstack_dir=self.dstack_dir)
        self.assertEqual(profile.token, conf.get_profile("other").token)
        self.assertEqual(default.token, conf.get_profile("default").token)

    @staticmethod
    def conf_example() -> Dict:
        return {"profiles": {"default": {"token": "token1"}, "other": {"token": "token2"}}}

    def create_yaml_file(self, path: Path, content: Dict):
        content = dump(content)
        file = path / self.config_filename
        file.write_text(content, encoding="utf-8")
