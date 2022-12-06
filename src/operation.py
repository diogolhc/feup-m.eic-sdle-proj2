import logging
from src.connection import request
from src.username import Username
from src.timeline import TimelineCache

log = logging.getLogger('timeline')

async def execute(data, local_port):
    log.debug("Connecting to local server on port %s", local_port)
    response = await request(data, "127.0.0.1", local_port)

    if response["status"] != "ok":
        print(f"Error: {response['error']}")
    return response

async def get(username, local_port):
    username = Username(username)
    response = await execute({
        "command": "get",
        "username": str(username)
    }, local_port)

    if response["status"] == "ok":
        print(TimelineCache.from_dict(response["timeline"]).pretty_str())

async def post(filepath, local_port):
    response = await execute({
        "command": "post",
        "filepath": filepath
    }, local_port)

    if response["status"] == "ok":
        print("Successfully posted to the timeline.")

async def sub(username, local_port):
    username = Username(username)
    response = await execute({
        "command": "sub",
        "username": str(username)
    }, local_port)

    if response["status"] == "ok":
        print(f"Successfully subscribed to {username}.")

async def unsub(username, local_port):
    username = Username(username)
    response = await execute({
        "command": "unsub",
        "username": str(username)
    }, local_port)

    if response["status"] == "ok":
        print(f"Successfully unsubscribed from {username}.")
