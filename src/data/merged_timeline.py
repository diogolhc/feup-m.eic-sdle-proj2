"""Classes to represent a Merged timeline of posts from several users."""
from tabulate import tabulate
from datetime import datetime

class MergedTimeline:
    def __init__(self, timelines):
        self.timelines = timelines
        self.posts = []

        for timeline in self.timelines:
            posts = timeline.posts

            for post in posts:
                post["username"] = timeline.username

            self.posts.append(posts)

    def from_serializable(data):
        return MergedTimeline(**data)

    def to_serializable(self):
        data = self.__dict__.copy()
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