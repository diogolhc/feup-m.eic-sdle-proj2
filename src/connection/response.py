"""Represents a response to a request, ok or error."""
class Response:
    def __init__(self, status, data=None):
        self.status = status
        self.data = data

    def to_dict(self):
        if self.data is None:
            return {"status": self.status}

        data = self.data.copy()
        data["status"] = self.status
            
        return data

class OkResponse(Response):
    def __init__(self, data=None):
        super().__init__("ok", data)

class ErrorResponse(Response):
    def __init__(self, message):
        super().__init__("error", {"error": message})
