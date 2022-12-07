"""A server that listens locally for commands from the user."""
from src.connection.base import BaseConnection
from src.connection.response import ErrorResponse
from src.data.username import Username
import logging

log = logging.getLogger("timeline")


class LocalConnection(BaseConnection):
    def __init__(self, handle_get, handle_post, handle_sub, handle_unsub, handle_view, handle_people_i_may_know):
        self.handle_get = handle_get
        self.handle_post = handle_post
        self.handle_sub = handle_sub
        self.handle_unsub = handle_unsub
        self.handle_view = handle_view
        self.handle_people_i_may_know = handle_people_i_may_know

    async def handle_command(self, command, message):
        if command == "get":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            if "max-posts" not in message:
                message["max-posts"] = None
            try:
                username = Username.from_str(message["username"])
            except ValueError:
                return ErrorResponse(f"Invalid username: {message['username']}")
            return await self.handle_get(username, message['max-posts'])
        elif command == "post":
            if "filepath" not in message:
                return ErrorResponse("No filepath provided.")
            return await self.handle_post(message["filepath"])
        elif command == "sub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            try:
                username = Username.from_str(message["username"])
            except ValueError:
                return ErrorResponse(f"Invalid username: {message['username']}")
            return await self.handle_sub(username)
        elif command == "unsub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            try:
                username = Username.from_str(message["username"])
            except ValueError:
                return ErrorResponse(f"Invalid username: {message['username']}")
            return await self.handle_unsub(username)
        elif command == "view":
            if "max-posts" not in message:
                message["max-posts"] = None
            
            return await self.handle_view(message['max-posts'])
        elif command == "people-i-may-know":
            if "max-people" not in message:
                message["max-people"] = None
            return await self.handle_people_i_may_know(message['max-people'])
        else:
            return ErrorResponse("Unknown command.")

    async def start(self, port):
        debug_message = lambda: log.debug(
            "Locally listening for instructions on port %s", port
        )
        await super().start("127.0.0.1", port, debug_message)
