"""Persistent storage for data of a given node."""
import os
import json
from pathlib import Path


class PersistentStorage:
    BASE_DIR = "data"

    def __init__(self, userid):
        self.base_dir = os.path.join(self.BASE_DIR, userid.to_filename())
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def create_dir(self, *paths):
        Path(self.get_path(*paths)).mkdir(parents=True, exist_ok=True)

    def get_path(self, *paths):
        return os.path.join(self.base_dir, *paths)

    def exists(self, *paths):
        return os.path.exists(self.get_path(*paths))

    def files(self):
        return os.listdir(self.base_dir)

    def write(self, data, *paths):
        with open(self.get_path(*paths), "w") as f:
            f.write(json.dumps(data))

    def read(self, *paths):
        with open(self.get_path(*paths), "r") as f:
            return json.loads(f.read())

    def delete(self, *paths):
        try:
            os.remove(self.get_path(*paths))
        except OSError:
            pass
