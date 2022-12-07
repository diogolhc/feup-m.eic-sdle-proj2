"""Represents a list of users this node is subscribed to."""

from src.data.username import Username

class Subscriptions:
    SUBSCRIPTIONS_FILE = "subscriptions.json"

    def __init__(self, subscriptions):
        self.subscriptions = subscriptions
    
    def subscribe(self, username):
        if username not in self.subscriptions:
            self.subscriptions.append(username)
            return True
        return False
    
    def unsubscribe(self, username):
        if username in self.subscriptions:
            self.subscriptions.remove(username)
            return True
        return False
    
    def from_serializable(data):
        return Subscriptions([Username.from_str(sub) for sub in data])

    def to_serializable(self):
        return [str(sub) for sub in self.subscriptions]

    def store(self, storage):
        storage.write(self.to_serializable(), Subscriptions.SUBSCRIPTIONS_FILE)

    def read(storage):
        if storage.exists(Subscriptions.SUBSCRIPTIONS_FILE):
            return Subscriptions.from_serializable(
                storage.read(Subscriptions.SUBSCRIPTIONS_FILE)
            )
        else:
            return Subscriptions([])
