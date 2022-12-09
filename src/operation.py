"""Operations made to the node via a local socket."""
import logging

from src.connection import request
from src.data.merged_timeline import MergedTimeline
from src.data.timeline import TimelineCache
from src.data.user import User

log = logging.getLogger("timeline")


async def execute(data, local_port):
    log.debug("Connecting to local server on port %s", local_port)
    response = await request(
        data, "127.0.0.1", local_port
    )  # TODO should we be using 127.0.0.1 hardcoded here instead of ip from the userid?

    if response["status"] != "ok":
        print(f"Error: {response['error']}")
    return response


async def get(userid, local_port, max_posts=None):
    userid = User(userid)
    response = await execute(
        {"command": "get", "userid": str(userid), "max-posts": max_posts}, local_port
    )

    if response["status"] == "ok":
        print(TimelineCache.from_serializable(response["timeline"]).pretty_str())


async def post(filepath, local_port):
    with open(filepath, "r") as f:
        content = f.read()
    response = await execute({"command": "post", "content": content}, local_port)

    if response["status"] == "ok":
        print("Successfully posted to the timeline.")


async def delete(post_id, local_port):
    response = await execute({"command": "delete", "post-id": post_id}, local_port)

    if response["status"] == "ok":
        print(f"Successfully deleted post with id={post_id}.")


async def sub(userid, local_port):
    userid = User(userid)
    response = await execute({"command": "sub", "userid": str(userid)}, local_port)

    if response["status"] == "ok":
        print(f"Successfully subscribed to {userid}.")


async def unsub(userid, local_port):
    userid = User(userid)
    response = await execute({"command": "unsub", "userid": str(userid)}, local_port)

    if response["status"] == "ok":
        print(f"Successfully unsubscribed from {userid}.")


async def view(local_port, max_posts=None):
    response = await execute({"command": "view", "max-posts": max_posts}, local_port)

    if response["status"] == "ok":
        print(MergedTimeline.from_serializable(response["timeline"]).pretty_str())


async def people_i_may_know(local_port, max_users=None):
    response = await execute(
        {"command": "people-i-may-know", "max-users": max_users}, local_port
    )

    if response["status"] == "ok":
        print(response["users"])
