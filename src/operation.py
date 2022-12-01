import json
import logging
import asyncio

log = logging.getLogger('timeline')

async def execute(data, local_port):
    log.debug("Connecting to local server on port %s", local_port)
    reader, writer = await asyncio.open_connection("127.0.0.1", local_port)

    log.debug("Sending message: %s", data)
    writer.write(json.dumps(data).encode())
    writer.write_eof()
    await writer.drain()
    
    data = await reader.read()
    response = json.loads(data.decode())
    log.debug("Received message: %s", response)
    writer.close()
    await writer.wait_closed()

    if response["status"] != "ok":
        print(f"Error: {response['error']}")
    return response


async def get(username, local_port):
    response = await execute({
        "command": "get",
        "username": username
    }, local_port)

    if response["status"] == "ok":
        print(f"Pretty output not implemented.\n{response}") # TODO

async def post(filepath, local_port):
    response = await execute({
        "command": "post",
        "filepath": filepath
    }, local_port)

    if response["status"] == "ok":
        print("Successfully posted to the timeline.")

async def sub(username, local_port):
    response = await execute({
        "command": "sub",
        "username": username
    }, local_port)

    if response["status"] == "ok":
        print(f"Successfully subscribed to {username}.")

async def unsub(username, local_port):
    response = await execute({
        "command": "unsub",
        "username": username
    }, local_port)

    if response["status"] == "ok":
        print(f"Successfully unsubscribed from {username}.")
