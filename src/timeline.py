class Timeline:
    def __init__(self, username, posts):
        self.username = username
        self.posts = posts

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
    
    def cache(self, max_posts, time_to_live):
        data = self.to_dict()
        data["posts"] = data["posts"][:max_posts]
        data["total_posts"] = len(self.posts)
        data["last_updated"] = datetime.now().isoformat()
        data["time_to_live"] = time_to_live
        return TimelineCache.from_dict(**data)


class TimelineCache(Timeline):
    def __init__(self, username, posts, total_posts, last_updated, time_to_live):
        super().__init__(username, posts)
        self.total_posts = total_posts
        self.last_updated = last_updated
        self.time_to_live = time_to_live
    
