from datetime import datetime, timedelta

class Timeline:
    def __init__(self, username, posts):
        self.username = username
        self.posts = posts
    
    def add_post(self, post):
        self.posts.append(post)

    def from_dict(data):
        return Timeline(**data)
    
    def to_dict(self):
        return self.__dict__
    
    def store(self, storage):
        storage.write(self.to_dict(), self.username)
    
    def read(self, storage, username=None):
        if storage.exists(username):
            return Timeline.from_dict(storage.read(username))
        else:
            return Timeline(username, [])
    
    def pretty_str(self):
        return f"Pretty output not implemented.\n{self.posts}" # TODO
    
    def cache(self, max_posts, time_to_live=None):
        data = self.to_dict()
        data["posts"] = data["posts"][:max_posts]
        data["total_posts"] = len(self.posts)
        now = datetime.now()
        data["last_updated"] = now.isoformat()
        data["valid_until"] = (now + timedelta(seconds=time_to_live)).isoformat()
        return TimelineCache.from_dict(**data)


class TimelineCache(Timeline):
    def __init__(self, username, posts, total_posts, last_updated, valid_until):
        super().__init__(username, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.valid_until = valid_until
    
    def cache(self, max_posts):
        data = self.to_dict()
        data["posts"] = data["posts"][:max_posts]

        return TimelineCache.from_dict(**data)
