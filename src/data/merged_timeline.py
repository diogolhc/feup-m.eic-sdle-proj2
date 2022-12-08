"""Classes to represent a Merged timeline of posts from several users."""
from datetime import datetime
from tabulate import tabulate

class MergedTimeline:
    def __init__(self, posts):
        self.posts = posts

    @staticmethod
    def from_timelines(timelines, max_posts):
        all_posts = []

        for timeline in timelines:
            posts = timeline.posts

            for post in posts:
                post["username"] = timeline.username

            all_posts.extend(posts)

        posts = [{
            "id": p["id"],
            "username": p["username"],
            "timestamp": datetime.fromisoformat(p["timestamp"]),
            "content": p["content"]
        } for p in all_posts]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        all_posts = [{
            "id": p["id"],
            "username": p["username"],
            "timestamp": p["timestamp"].isoformat(),
            "content": p["content"]
        } for p in posts]

        return MergedTimeline(all_posts if max_posts is None else all_posts[:max_posts])

    @staticmethod
    def from_serializable(data):
        return MergedTimeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()

        for p in data["posts"]:
            p["username"] = str(p["username"])

        return data

    def pretty_str(self):
        posts = [{
            "id": p["id"],
            "username": p["username"],
            "timestamp": datetime.fromisoformat(p["timestamp"]),
            "content": p["content"]
        } for p in self.posts]

        posts.sort(key=lambda x: x["timestamp"], reverse=True)

        def table_row(post):
            return [
                post["id"],
                post["username"],
                post["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                post["content"]
            ]

        tabledata = [table_row(post) for post in posts]
        return tabulate(tabledata, headers=["id", "username", "time", "content"])
