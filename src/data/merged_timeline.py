"""Classes to represent a Merged timeline of posts from several users."""
from datetime import datetime
import copy
from tabulate import tabulate
from src.data.user import User


class MergedTimeline:
    def __init__(self, posts):
        self.posts = posts

    @staticmethod
    def from_timelines(timelines, max_posts):
        all_posts = []

        for timeline in timelines:
            posts = copy.deepcopy(timeline.posts)

            for post in posts:
                post["userid"] = timeline.userid

            all_posts.extend(posts)

        posts = [
            {
                "id": p["id"],
                "userid": p["userid"],
                "timestamp": datetime.fromisoformat(p["timestamp"]),
                "content": p["content"],
            }
            for p in all_posts
        ]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [
            {
                "id": p["id"],
                "userid": p["userid"],
                "timestamp": p["timestamp"].isoformat(),
                "content": p["content"],
            }
            for p in posts
        ]

        return MergedTimeline(all_posts if max_posts is None else all_posts[:max_posts])

    @staticmethod
    def from_serializable(data):
        for p in data["posts"]:
            p["userid"] = User.from_str(p["userid"])

        return MergedTimeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()

        for p in data["posts"]:
            p["userid"] = str(p["userid"])

        return data

    def pretty_str(self):
        posts = [
            {
                "userid": p["userid"],
                "timestamp": datetime.fromisoformat(p["timestamp"]),
                "content": p["content"],
            }
            for p in self.posts
        ]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        def table_row(post):
            return [
                str(post["userid"]),
                post["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                post["content"],
            ]

        tabledata = [table_row(post) for post in posts]
        return tabulate(tabledata, headers=["userid", "time", "content"])
