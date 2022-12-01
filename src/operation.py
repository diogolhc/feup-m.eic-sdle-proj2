import json
import asyncio
import logging

log = logging.getLogger('timeline')

async def execute(data, local_port):
    log.debug("Connecting to local server on port %s", local_port)
    reader, writer = await asyncio.open_connection("127.0.0.1", local_port)

    message = json.dumps(data)
    log.debug("Sending message: %s", message)
    writer.write(message.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    data = await reader.read()
    message = data.decode()
    log.debug("Received message: %s", message)

    print(message)


def get(username, local_port, debug):
    asyncio.run(execute({
        "command": "get",
        "username": username
    }, local_port), debug=debug)

def post(filepath, local_port, debug):
    asyncio.run(execute({
        "command": "post",
        "filepath": filepath
    }, local_port), debug=debug)

def sub(username, local_port, debug):
    asyncio.run(execute({
        "command": "sub",
        "username": username
    }, local_port), debug=debug)

def unsub(username, local_port, debug):
    asyncio.run(execute({
        "command": "unsub",
        "username": username
    }, local_port), debug=debug)
