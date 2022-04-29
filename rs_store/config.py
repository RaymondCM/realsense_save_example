import json
import pathlib

import yaml


class Config:
    def __init__(self, path):
        path = pathlib.Path(path)
        if not str(path).endswith(".yaml"):
            print(f"File must be a .yaml file not {path.name}")
        with path.open('r') as fh:
            self._data = yaml.safe_load(fh)
        advanced_path = pathlib.Path(self._data["advanced_config"])
        if '/' not in str(advanced_path):
            advanced_path = pathlib.Path(__file__).parent.parent / "configs" / advanced_path
        with advanced_path.open('r') as fh:
            self._advanced_config = json.load(fh)
        self._advanced_config_str = str(self._advanced_config).replace("'", '\"')

    def __getitem__(self, item):
        if item in self._data:
            return self._data[item]
        if item in self._advanced_config:
            return self._advanced_config[item]
        raise KeyError(f"Item '{item}' does not exist")

    def __str__(self):
        return str(self._data) + str(self._advanced_config)

    def has_key(self, key):
        try:
            self.__getitem__(key)
        except KeyError:
            return False
        return True

    def __getattr__(self, item):
        return self.__getitem__(item)

    def __bool__(self):
        return bool(self._data)

    @property
    def rs(self):
        return self._advanced_config

    @property
    def rs_str(self):
        return self._advanced_config_str
