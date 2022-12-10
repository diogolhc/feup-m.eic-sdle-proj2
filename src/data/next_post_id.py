"""Represents the current post id of the local user."""


class NextPostId:
    NEXT_POST_ID_FILE = "next_post_id.json"
    START_ID = 0

    def __init__(self, id):
        self.id = id
    
    def get_and_advance(self):
        id = self.id
        self.id += 1
        return id
    
    def rollback(self):
        self.id -= 1

    @staticmethod
    def from_serializable(data):
        return NextPostId(**data)

    def to_serializable(self):
        return self.__dict__.copy()

    def store(self, storage):
        storage.write(self.to_serializable(), NextPostId.NEXT_POST_ID_FILE)

    @staticmethod
    def read(storage):
        if storage.exists(NextPostId.NEXT_POST_ID_FILE):
            return NextPostId.from_serializable(
                storage.read(NextPostId.NEXT_POST_ID_FILE)
            )
        else:
            return NextPostId(NextPostId.START_ID)
