"""Operations made to the node via a local socket."""
import logging
from src.connection import request
from src.data.username import Username
from src.data.timeline import TimelineCache
from src.data.merged_timeline import MergedTimeline

log = logging.getLogger("timeline")


async def execute(data, local_port):
    log.debug("Connecting to local server on port %s", local_port)
    response = await request(data, "127.0.0.1", local_port)

    if response["status"] != "ok":
        print(f"Error: {response['error']}")
    return response


async def get(username, local_port, max_posts=None):
    username = Username(username)
    response = await execute({"command": "get", "username": str(username), "max-posts": max_posts}, local_port)

    if response["status"] == "ok":
        print(TimelineCache.from_serializable(response["timeline"]).pretty_str())


async def post(filepath, local_port):
    response = await execute({"command": "post", "filepath": filepath}, local_port)

    if response["status"] == "ok":
        print("Successfully posted to the timeline.")


async def sub(username, local_port):
    username = Username(username)
    response = await execute({"command": "sub", "username": str(username)}, local_port)

    if response["status"] == "ok":
        print(f"Successfully subscribed to {username}.")


async def unsub(username, local_port):
    username = Username(username)
    response = await execute(
        {"command": "unsub", "username": str(username)}, local_port
    )

    if response["status"] == "ok":
        print(f"Successfully unsubscribed from {username}.")

async def view(local_port, max_posts=None):
    response = await execute({"command": "view", "max-posts": max_posts}, local_port)

    if response["status"] == "ok":
        print(MergedTimeline.from_serializable(response["timeline"]).pretty_str())

async def people_i_may_know(local_port, max_users=None):
    response = await execute({"command": "people-i-may-know", "max-users": max_users}, local_port)

    if response["status"] == "ok":
        print(response["users"].pretty_str())
