"""Represents a response to a request, ok or error."""
class Response:
    def __init__(self, status, data=None, warnings=None):
        self.status = status
        self.data = data
        self.warnings = warnings

    def to_dict(self):
        if self.data is None:
            if self.warnings is None:
                return {"status": self.status}
            else: 
                return {"status": self.status, "warnings": self.warnings}
        data = self.data.copy()
        data["status"] = self.status

        if self.warnings is not None:
            data["warnings"] = self.warnings
            
        return data

class OkResponse(Response):
    def __init__(self, data=None):
        super().__init__("ok", data)

class ErrorResponse(Response):
    def __init__(self, message):
        super().__init__("error", {"error": message})
