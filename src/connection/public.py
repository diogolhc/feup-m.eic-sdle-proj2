from src.connection.base import BaseConnection
from src.connection.response import ErrorResponse
import logging

log = logging.getLogger('timeline')

class PublicConnection(BaseConnection):
    def __init__(self, handle_get_timeline):
        self.handle_get_timeline = handle_get_timeline

    async def handle_command(self, command, message):
        if command == "get-timeline":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_get(message["username"])
        else:
            return ErrorResponse("Unknown command.")

    async def start(self, username):
        debug_message = lambda: log.debug("Listening for other nodes on %s:%s", username[0], username[1])
        await super().start(username[0], username[1], debug_message)
