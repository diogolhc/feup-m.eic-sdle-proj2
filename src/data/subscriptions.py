"""Represents a list of users this node is subscribed to."""

from src.data.userid import User


class Subscriptions:
    SUBSCRIPTIONS_FILE = "subscriptions.json"

    def __init__(self, subscriptions):
        self.subscriptions = subscriptions

    def subscribe(self, userid):
        if userid not in self.subscriptions:
            self.subscriptions.append(userid)
            return True
        return False

    def unsubscribe(self, userid):
        if userid in self.subscriptions:
            self.subscriptions.remove(userid)
            return True
        return False

    @staticmethod
    def from_serializable(data):
        return Subscriptions([User.from_str(sub) for sub in data])

    def to_serializable(self):
        return [str(sub) for sub in self.subscriptions]

    def store(self, storage):
        storage.write(self.to_serializable(), Subscriptions.SUBSCRIPTIONS_FILE)

    @staticmethod
    def read(storage):
        if storage.exists(Subscriptions.SUBSCRIPTIONS_FILE):
            return Subscriptions.from_serializable(
                storage.read(Subscriptions.SUBSCRIPTIONS_FILE)
            )
        else:
            return Subscriptions([])
