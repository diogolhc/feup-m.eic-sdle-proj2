"""Classes to represent a timeline of posts from a user and a cached timeline."""
from datetime import datetime, timedelta
import os
from tabulate import tabulate
from src.data.user import User


class Timeline:
    TIMELINES_FOLDER = "timelines"
    DEFAULT_CACHE_TIME_TO_LIVE = 60  # TODO good value?

    def __init__(self, userid, posts):
        self.userid = userid
        self.posts = posts

    def is_valid(self):
        return True  # A non-cached timeline is always valid

    def add_post(self, post):
        self.posts.append(
            {
                "id": len(
                    self.posts
                ),  # TODO if we ever want to support a delete operation, this is not correct. We would need to use a real counter in persistent storage.
                "timestamp": datetime.now().isoformat(),
                "content": post,
            }
        )
        return self.posts[-1]

    def remove_post(self, post):
        self.posts.remove(post)

    @staticmethod
    def from_serializable(data):
        if "valid_until" in data:
            return TimelineCache.from_serializable(data)
        data["userid"] = User.from_str(data["userid"])
        return Timeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()
        data["userid"] = str(data["userid"])
        return data

    @staticmethod
    def get_file(storage, userid):
        return os.path.join(Timeline.TIMELINES_FOLDER, f"{userid.to_filename()}.json")

    @staticmethod
    def exists(storage, userid):
        return storage.exists(Timeline.get_file(storage, userid))

    def store(self, storage):
        storage.write(self.to_serializable(), Timeline.get_file(storage, self.userid))

    @staticmethod
    def read(storage, userid):
        if Timeline.exists(storage, userid):
            return Timeline.from_serializable(
                storage.read(Timeline.get_file(storage, userid))
            )
        else:
            return Timeline(userid, [])

    @staticmethod
    def delete(storage, userid):
        storage.delete(Timeline.get_file(storage, userid))

    def pretty_str(self):
        posts = [
            {
                "id": p["id"],
                "timestamp": datetime.fromisoformat(p["timestamp"]),
                "content": p["content"],
            }
            for p in self.posts
        ]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        def table_row(post):
            return [
                post["id"],
                post["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                post["content"],
            ]

        tabledata = [table_row(post) for post in posts]
        return tabulate(tabledata, headers=["id", "time", "content"])

    def cache(self, max_posts, time_to_live=None):

        posts = [
            {
                "id": p["id"],
                "timestamp": datetime.fromisoformat(p["timestamp"]),
                "content": p["content"],
            }
            for p in self.posts
        ]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [
            {
                "id": p["id"],
                "timestamp": p["timestamp"].isoformat(),
                "content": p["content"],
            }
            for p in posts
        ]

        now = datetime.now()
        return TimelineCache(
            userid=self.userid,
            posts=all_posts if max_posts is None else all_posts[:max_posts],
            total_posts=len(self.posts),
            last_updated=now,
            valid_until=now
            + timedelta(
                seconds=time_to_live
                if time_to_live is not None
                else Timeline.DEFAULT_CACHE_TIME_TO_LIVE
            ),
        )


class TimelineCache(Timeline):
    def __init__(self, userid, posts, total_posts, last_updated, valid_until):
        super().__init__(userid, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.valid_until = valid_until

    def is_valid(self):
        return True # TODO adjust valid until for a reasonable interval
        return self.valid_until is None or datetime.now() < self.valid_until

    def cache(self, max_posts):
        posts = [
            {
                "id": p["id"],
                "timestamp": datetime.fromisoformat(p["timestamp"]),
                "content": p["content"],
            }
            for p in self.posts
        ]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [
            {
                "id": p["id"],
                "timestamp": p["timestamp"].isoformat(),
                "content": p["content"],
            }
            for p in posts
        ]

        return TimelineCache(
            userid=self.userid,
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
        data["userid"] = User.from_str(data["userid"])
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if data["valid_until"] is not None:
            data["valid_until"] = datetime.fromisoformat(data["valid_until"])
        return TimelineCache(**data)
