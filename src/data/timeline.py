"""Classes to represent a timeline of posts from a user and a cached timeline."""
from datetime import datetime, timedelta
import dateutil.parser
from src.data.username import Username
import os


class Timeline:
    TIMELINES_FOLDER = "timelines"

    def __init__(self, username, posts):
        self.username = username
        self.posts = posts
    
    def is_valid(self):
        return True # A non-cached timeline is always valid

    def add_post(self, post):
        self.posts.append({
            "id": len(self.posts), # TODO if we ever want to support a delete operation, this is not correct. We would need to use a real counter in persistent storage.
            "timestamp": datetime.now().isoformat(),
            "content": post,
        })
        return self.posts[-1]

    def remove_post(self, post):
        self.posts.remove(post)

    def from_serializable(data):
        if "valid_until" in data:
            return TimelineCache.from_serializable(data)
        data["username"] = Username.from_str(data["username"])
        return Timeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()
        data["username"] = str(data["username"])
        return data

    def get_file(storage, username):
        return os.path.join(Timeline.TIMELINES_FOLDER, f"{username.to_filename()}.json")

    def exists(storage, username):
        return storage.exists(Timeline.get_file(storage, username))

    def store(self, storage):
        storage.write(self.to_serializable(), Timeline.get_file(storage, self.username))

    def read(storage, username):
        if Timeline.exists(storage, username):
            return Timeline.from_serializable(
                storage.read(Timeline.get_file(storage, username))
            )
        else:
            return Timeline(username, [])
    
    def delete(storage, username):
        storage.delete(Timeline.get_file(storage, username))

    def pretty_str(self):
        return f"Pretty output not implemented.\n{self.posts}"  # TODO

    def cache(self, max_posts, time_to_live=None):
        now = datetime.now()
        return TimelineCache(
            username=self.username,
            posts=self.posts if max_posts is None else self.posts[:max_posts],
            total_posts=len(self.posts),
            last_updated=now,
            valid_until=now + timedelta(seconds=time_to_live),
        )


class TimelineCache(Timeline):
    def __init__(self, username, posts, total_posts, last_updated, valid_until):
        super().__init__(username, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.valid_until = valid_until
    
    def is_valid(self):
        return self.valid_until is None or datetime.now() < self.valid_until

    def cache(self, max_posts):
        return TimelineCache(
            username=self.username,
            posts=self.posts if max_posts is None else self.posts[:max_posts],
            total_posts=self.total_posts,
            last_updated=self.last_updated,
            valid_until=self.valid_until,
        )

    def to_serializable(self):
        data = super().to_serializable()
        data["last_updated"] = data["last_updated"].isoformat()
        if data["valid_until"] is not None:
            data["valid_until"] = data["valid_until"].isoformat()
        return data

    def from_serializable(data):
        data["username"] = Username.from_str(data["username"])
        data["last_updated"] = dateutil.parser.parse(data["last_updated"])
        if data["valid_until"] is not None:
            data["valid_until"] = dateutil.parser.parse(data["valid_until"])
        return TimelineCache(**data)
