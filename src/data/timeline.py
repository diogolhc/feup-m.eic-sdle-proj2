"""Classes to represent a timeline of posts from a user and a cached timeline."""
from datetime import datetime, timedelta
import os
from tabulate import tabulate
from src.data.username import Username

class Timeline:
    TIMELINES_FOLDER = "timelines"
    DEFAULT_CACHE_TIME_TO_LIVE = 60 # TODO good value?

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

    @staticmethod
    def from_serializable(data):
        if "valid_until" in data:
            return TimelineCache.from_serializable(data)
        data["username"] = Username.from_str(data["username"])
        return Timeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()
        data["username"] = str(data["username"])
        return data

    @staticmethod
    def get_file(storage, username):
        return os.path.join(Timeline.TIMELINES_FOLDER, f"{username.to_filename()}.json")

    @staticmethod
    def exists(storage, username):
        return storage.exists(Timeline.get_file(storage, username))

    def store(self, storage):
        storage.write(self.to_serializable(), Timeline.get_file(storage, self.username))

    @staticmethod
    def read(storage, username):
        if Timeline.exists(storage, username):
            return Timeline.from_serializable(
                storage.read(Timeline.get_file(storage, username))
            )
        else:
            return Timeline(username, [])

    @staticmethod
    def delete(storage, username):
        storage.delete(Timeline.get_file(storage, username))

    def pretty_str(self):
        posts = [{
            "id": p["id"],
            "timestamp": datetime.fromisoformat(p["timestamp"]),
            "content": p["content"]
        } for p in self.posts]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        def table_row(post):
            return [
                post["id"], 
                post["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), 
                post["content"]
            ]

        tabledata = [table_row(post) for post in posts]
        return tabulate(tabledata, headers=["id", "time", "content"])

    def cache(self, max_posts, time_to_live=None):

        posts = [{
            "id": p["id"],
            "timestamp": datetime.fromisoformat(p["timestamp"]),
            "content": p["content"]
        } for p in self.posts]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [{
            "id": p["id"],
            "timestamp": p["timestamp"].isoformat(),
            "content": p["content"]
        } for p in posts]

        now = datetime.now()
        return TimelineCache(
            username=self.username,
            posts=all_posts if max_posts is None else all_posts[:max_posts],
            total_posts=len(self.posts),
            last_updated=now,
            valid_until=now + timedelta(seconds=time_to_live if time_to_live is not None else Timeline.DEFAULT_CACHE_TIME_TO_LIVE),
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
        posts = [{
            "id": p["id"],
            "timestamp": datetime.fromisoformat(p["timestamp"]),
            "content": p["content"]
        } for p in self.posts]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [{
            "id": p["id"],
            "timestamp": p["timestamp"].isoformat(),
            "content": p["content"]
        } for p in posts]

        return TimelineCache(
            username=self.username,
            posts=all_posts if max_posts is None else all_posts[:max_posts],
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

    @staticmethod
    def from_serializable(data):
        data["username"] = Username.from_str(data["username"])
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if data["valid_until"] is not None:
            data["valid_until"] = datetime.fromisoformat(data["valid_until"])
        return TimelineCache(**data)
