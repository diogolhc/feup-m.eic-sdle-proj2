"""Base class for LocalConnection and PublicConnection."""
import asyncio
import json
import logging

from src.connection.response import ErrorResponse

log = logging.getLogger('timeline')

class BaseConnection:
    async def handle_command(self, command, message):
        """Virtual method to be implemented by subclasses."""
        pass

    async def handle_request(self, reader, writer):
        data = await reader.read()
        message = json.loads(data.decode())
        addr = writer.get_extra_info('peername')

        log.debug("Received from %r: %r", addr, message)

        if "command" in message:
            response = await self.handle_command(message["command"], message)
        else:
            response = ErrorResponse("No command provided.")

        response = response.to_dict()
        writer.write(json.dumps(response).encode())
        log.debug("Responded to %r: %r", addr, response)
        await writer.drain()
        writer.close()

    async def start(self, ip, port, debug_log=None):
        server = await asyncio.start_server(self.handle_request, ip, port)

        if debug_log is not None:
            debug_log()

        async with server:
            await server.serve_forever()
