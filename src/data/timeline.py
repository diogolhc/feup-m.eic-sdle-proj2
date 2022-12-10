"""Classes to represent a timeline of posts from a user and a cached timeline."""
import os
from datetime import datetime, timedelta

from tabulate import tabulate

from src.data.user import User


class Timeline:
    TIMELINES_FOLDER = "timelines"

    def __init__(self, userid, posts):
        self.userid = userid
        self.posts = posts

    def is_valid(self):
        return True  # A non-cached timeline is always valid

    def add_post(self, post, post_id): # post_id was already validated
        self.posts.append(
            {
                "id": post_id,
                "timestamp": datetime.now().isoformat(),
                "content": post,
            }
        )
        return self.posts[-1]

    def remove_post(self, post):
        try:
            self.posts.remove(post)
            return True
        except ValueError:
            return False

    def get_post_by_id(self, post_id):
        for post in self.posts:
            if post["id"] == post_id:
                return post
        return None

    def remove_post_by_id(self, post_id):
        post = self.get_post_by_id(post_id)
        if post is not None:
            return self.remove_post(post)
        return False

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
    def get_file(userid):
        return os.path.join(Timeline.TIMELINES_FOLDER, f"{userid.to_filename()}.json")

    @staticmethod
    def exists(storage, userid):
        return storage.exists(Timeline.get_file(userid))

    def store(self, storage):
        storage.write(self.to_serializable(), Timeline.get_file(self.userid))

    @staticmethod
    def read(storage, userid):
        if Timeline.exists(storage, userid):
            return Timeline.from_serializable(
                storage.read(Timeline.get_file(userid))
            )
        else:
            return Timeline(userid, [])

    @staticmethod
    def delete(storage, userid):
        storage.delete(Timeline.get_file(userid))

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
        valid_until = None
        if time_to_live is not None:
            valid_until = now + timedelta(seconds=time_to_live)
        return TimelineCache(
            userid=self.userid,
            posts=all_posts if max_posts is None else all_posts[:max_posts],
            total_posts=len(self.posts),
            last_updated=now,
            valid_until=valid_until,
        )


class TimelineCache(Timeline):
    def __init__(self, userid, posts, total_posts, last_updated, valid_until):
        super().__init__(userid, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.valid_until = valid_until

    def is_valid(self):
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
