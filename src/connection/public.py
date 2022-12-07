"""A server that listens to other nodes."""
from src.connection.base import BaseConnection
from src.connection.response import ErrorResponse
from src.data.username import Username
import logging

log = logging.getLogger("timeline")


class PublicConnection(BaseConnection):
    def __init__(self, handle_get_timeline):
        self.handle_get_timeline = handle_get_timeline

    async def handle_command(self, command, message):
        if command == "get-timeline":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            try:
                username = Username.from_str(message["username"])
            except ValueError:
                return ErrorResponse(f"Invalid username: {message['username']}")
            return await self.handle_get_timeline(username, 10)  # TODO max posts
        else:
            return ErrorResponse("Unknown command.")

    async def start(self, username):
        debug_message = lambda: log.debug("Listening for other nodes on %s", username)
        await super().start(username.ip, username.port, debug_message)
