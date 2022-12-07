"""Classes to represent a timeline of posts from a user and a cached timeline."""
from tabulate import tabulate
from datetime import datetime, timedelta
from src.data.username import Username
import os


class Timeline:
    TIMELINES_FOLDER = "timelines"

    def __init__(self, username, posts):
        self.username = username
        self.posts = posts

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

    def pretty_str(self):
        p = list(map(lambda p: {"id": p["id"],
                                "timestamp": datetime.fromisoformat(p["timestamp"]),
                                "content": p["content"]}, self.posts))

        p = sorted(p, key=lambda x: x["timestamp"], reverse=True)

        return tabulate([[post["id"], post["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), post["content"]] for post in p], headers=["id", "time", "content"])

    def cache(self, max_posts, time_to_live=None):
        data = self.to_serializable()
        data["posts"] = data["posts"][:max_posts]
        data["total_posts"] = len(self.posts)
        now = datetime.now()
        data["last_updated"] = now.isoformat()
        if time_to_live is None:
            data["valid_until"] = None
        else:
            data["valid_until"] = (now + timedelta(seconds=time_to_live)).isoformat()
        return TimelineCache.from_serializable(data)


class TimelineCache(Timeline):
    def __init__(self, username, posts, total_posts, last_updated, valid_until):
        super().__init__(username, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.valid_until = valid_until

    def cache(self, max_posts):
        data = self.to_serializable()
        data["posts"] = data["posts"][:max_posts]

        return TimelineCache.from_serializable(**data)

    def from_serializable(data):
        data["username"] = Username.from_str(data["username"])
        return TimelineCache(**data)
