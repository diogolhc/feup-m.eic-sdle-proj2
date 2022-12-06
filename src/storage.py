import os
import json
from pathlib import Path

class PersistentStorage:
    BASE_DIR = "data"

    def __init__(self, id):
        self.id = id
        self.base_dir = os.path.join(self.BASE_DIR, id.to_filename())
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def get_path(self, username=None): # TODO storage uses username
        if username is None:
            username = self.id
        return os.path.join(self.base_dir, username.to_filename()) + ".json"

    def exists(self, username=None):
        return os.path.exists(self.get_path(username))
    
    def files(self):
        return os.listdir(self.base_dir)

    def write(self, data, username=None):
        with open(self.get_path(username), "w") as f:
            f.write(json.dumps(data))
    
    def read(self, username=None):
        with open(self.get_path(username), "r") as f:
            return json.loads(f.read())
