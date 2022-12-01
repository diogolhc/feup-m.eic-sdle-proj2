import asyncio
import json
import logging
from kademlia.network import Server
from response import OkResponse, ErrorResponse

log = logging.getLogger('timeline')

class Node:
    def __init__(self):
        self.node_connection = None
    
    async def handle_get(self, username):
        return ErrorResponse("Not implemented.") # TODO
    
    async def handle_post(self, filepath):
        return ErrorResponse("Not implemented.") # TODO
    
    async def handle_sub(self, username):
        return ErrorResponse("Not implemented.") # TODO

    async def handle_unsub(self, username):
        return ErrorResponse("Not implemented.") # TODO

    async def handle_command(self, command, message):
        if command == "get":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_get(message["username"])
        elif command == "post":
            if "filepath" not in message:
                return ErrorResponse("No filepath provided.")
            return await self.handle_post(message["filepath"])
        elif command == "sub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_sub(message["username"])
        elif command == "unsub":
            if "username" not in message:
                return ErrorResponse("No username provided.")
            return await self.handle_unsub(message["username"])
        else:
            return ErrorResponse("Unknown command.")

    async def handle_local_request(self, reader, writer):
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

    async def start_kademlia(self, port, bootstrap_nodes):
        self.node_connection = Server()

        await self.node_connection.listen(port)
        
        if len(bootstrap_nodes) > 0:
            log.debug("Bootstrapping with %s", bootstrap_nodes)
            await self.node_connection.bootstrap(bootstrap_nodes)
        
        log.debug("Ready to listen to peers on port %s", port)
    
    async def start_local(self, local_port):
        local_server = await asyncio.start_server(self.handle_local_request, '127.0.0.1', local_port)

        log.debug("Locally listening for instructions on port %s", local_port)

        async with local_server:
            await local_server.serve_forever()

    async def run(self, port, bootstrap_nodes, local_port):
        await self.start_kademlia(port, bootstrap_nodes)
        await self.start_local(local_port)
