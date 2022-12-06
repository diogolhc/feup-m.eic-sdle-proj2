from datetime import datetime, timedelta
from src.username import Username

class Timeline:
    def __init__(self, username, posts):
        self.username = username
        self.posts = posts
    
    def add_post(self, post):
        self.posts.append(post) # TODO post object with timestamp and id

    def from_dict(data):
        data['username'] = Username.from_str(data['username'])
        return Timeline(**data)
    
    def to_dict(self):
        data = self.__dict__.copy()
        data['username'] = str(data['username'])
        return data
    
    def store(self, storage):
        storage.write(self.to_dict(), self.username) # TODO storage uses username
    
    def read(storage, username):
        if storage.exists(username): # TODO storage uses username
            return Timeline.from_dict(storage.read(username)) # TODO storage uses username
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
        if time_to_live is None:
            data["valid_until"] = None
        else:
            data["valid_until"] = (now + timedelta(seconds=time_to_live)).isoformat()
        return TimelineCache.from_dict(data)


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
    
    def from_dict(data):
        data['username'] = Username.from_str(data['username'])
        return TimelineCache(**data)
