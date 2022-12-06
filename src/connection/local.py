from src.connection.base import BaseConnection
from src.connection.response import ErrorResponse
from src.username import Username
import logging

log = logging.getLogger('timeline')

class LocalConnection(BaseConnection):
    def __init__(self, handle_get, handle_post, handle_sub, handle_unsub):
        self.handle_get = handle_get
        self.handle_post = handle_post
        self.handle_sub = handle_sub
        self.handle_unsub = handle_unsub

    async def handle_command(self, command, message):
        if command == "get":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_get(Username.from_str(message["username"]), 10) # TODO handle username errors TODO max posts
        elif command == "post":
            if "filepath" not in message:
                return ErrorResponse("No filepath provided.")
            return await self.handle_post(message["filepath"])
        elif command == "sub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_sub(Username.from_str(message["username"]))
        elif command == "unsub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_unsub(Username.from_str(message["username"]))
        else:
            return ErrorResponse("Unknown command.")

    async def start(self, port):
        debug_message = lambda: log.debug("Locally listening for instructions on port %s", port)
        await super().start('127.0.0.1', port, debug_message)
