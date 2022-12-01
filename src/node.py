import asyncio
import json
import logging
from kademlia.network import Server

log = logging.getLogger('timeline')

async def start_async(port, bootstrap_nodes, local_port):
    server = Server()

    async def handle_operation(reader, writer):
        data = await reader.read()
        message = json.loads(data.decode())
        addr = writer.get_extra_info('peername')

        log.debug("Received from %r: %r", message, addr)

        print(await server.get("foo"))
        await server.set("foo", "bar")

        writer.write("RESPOSTA".encode())
        await writer.drain()
        writer.close()

    await server.listen(port)
    
    if len(bootstrap_nodes) > 0:
            await server.bootstrap(bootstrap_nodes)

    print(await server.get("foo"))
    
    server2 = await asyncio.start_server(handle_operation, '127.0.0.1', local_port)

    log.debug("Locally listening for instructions on port %s", local_port)

    async with server2:
       await server2.serve_forever()

    

def start(port, bootstrap_nodes, local_port, debug):
    asyncio.run(start_async(port, bootstrap_nodes, local_port), debug=debug)