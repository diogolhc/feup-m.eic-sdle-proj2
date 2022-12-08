"""A server that listens to other nodes."""
from src.connection.base import BaseConnection
from src.connection.response import ErrorResponse
from src.data.user import User
import logging

log = logging.getLogger("timeline")


class PublicConnection(BaseConnection):
    def __init__(self, handle_get_timeline):
        self.handle_get_timeline = handle_get_timeline

    async def handle_command(self, command, message):
        if command == "get-timeline":
            if "userid" not in message:
                return ErrorResponse("No userid provided.")
            if "max-posts" not in message:
                message["max-posts"] = None
            try:
                userid = User.from_str(message["userid"])
            except ValueError:
                return ErrorResponse(f"Invalid userid: {message['userid']}")
            return await self.handle_get_timeline(userid, message["max-posts"])
        else:
            return ErrorResponse("Unknown command.")

    async def start(self, userid):
        debug_message = lambda: log.debug("Listening for other nodes on %s", userid)
        await super().start(userid.ip, userid.port, debug_message)
