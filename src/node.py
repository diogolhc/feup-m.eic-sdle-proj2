"""Class for the node that runs the timeline service."""
import asyncio
import logging
import random as rnd

from src.connection import (ErrorResponse, KademliaConnection, LocalConnection,
                            OkResponse, PublicConnection, request)
from src.data.merged_timeline import MergedTimeline
from src.data.next_post_id import NextPostId
from src.data.storage import PersistentStorage
from src.data.subscriptions import Subscriptions
from src.data.timeline import Timeline
from src.data.user import User

log = logging.getLogger("timeline")


class Node:
    DEFAULT_SLEEP_TIME_BETWEEN_CACHING = 120
    DEFAULT_MAX_CACHED_POSTS = 20
    DEFAULT_PUBLIC_PORT = 8000
    DEFAULT_KADEMLIA_PORT = 8468
    DEFAULT_LOCAL_PORT = 8600
    TRY_ANOTHER_SUBSCRIBER_PROBABILITY = 0.75
    TRY_ANOTHER_SUBSCRIBER_PROBABILITY_DECAY = 0.5

    def __init__(self, userid):
        self.userid = User(userid)

        # Connections
        self.kademlia_connection = KademliaConnection(self.userid)
        self.local_connection = LocalConnection(
            self.handle_get,
            self.handle_post,
            self.handle_remove,
            self.handle_sub,
            self.handle_unsub,
            self.handle_view,
            self.handle_people_i_may_know
        )
        self.public_connection = PublicConnection(self.handle_public_get)

        # Storage
        self.storage = PersistentStorage(self.userid)
        self.storage.create_dir(Timeline.TIMELINES_FOLDER)

        try:
            self.timeline = Timeline.read(self.storage, self.userid)
        except Exception as e:
            log.error("Could not read timeline from storage.", e)
            exit(1)

        try:
            self.subscriptions = Subscriptions.read(self.storage)
        except Exception as e:
            log.error("Could not read subscriptions from storage.", e)
            exit(1)

        try:
            self.next_post_id = NextPostId.read(self.storage)
        except Exception as e:
            log.error("Could not read next post id from storage.", e)
            exit(1)

    async def get_local(self, userid, max_posts):
        # get own timeline
        if userid == self.userid:
            return self.timeline.cache(max_posts, self.time_to_live)

        # get cached timeline
        if Timeline.exists(self.storage, userid):
            try:
                timeline = Timeline.read(self.storage, userid)
                if timeline.is_valid():
                    return timeline.cache(max_posts)
                else:
                    Timeline.delete(self.storage, userid)

            except Exception as e:
                log.error("Could not read timeline from storage.", e)

        return None

    async def get_peers(
        self, userid, max_posts, subscribers=None, last_updated_after=None
    ):
        # get timeline directly from owner
        data = {
            "command": "get-timeline",
            "userid": str(userid),
            "max-posts": max_posts,
        }

        log.debug("Connecting to %s", userid)

        try:
            response = await request(data, userid.ip, userid.port)
            if response["status"] == "ok":
                return OkResponse({"timeline": response["timeline"]})
        except Exception as e:
            log.error("Could not connect to %s: %s", userid, e)

        # get timeline from a subscriber
        if subscribers is None:
            subscribers = await self.kademlia_connection.get_subscribers(userid)
            if subscribers is None:
                return ErrorResponse(f"No available source found.")

        timeline = None
        last_update_check = last_updated_after
        heuristic_probability = self.TRY_ANOTHER_SUBSCRIBER_PROBABILITY
        rnd.shuffle(subscribers)

        for subscriber in subscribers:
            if self.userid == subscriber:
                continue

            log.debug("Connecting to subscriber %s", subscriber)
            response = await request(data, subscriber.ip, subscriber.port)

            if response["status"] == "ok":
                response_timeline = Timeline.from_serializable(response["timeline"])
                if last_update_check and response_timeline.last_updated <= last_update_check:
                    if rnd.random() >= heuristic_probability:
                        break
                    heuristic_probability *= self.TRY_ANOTHER_SUBSCRIBER_PROBABILITY_DECAY
                else:
                    timeline = response_timeline
                    last_update_check = response_timeline.last_updated
            else:
                log.debug("Subscriber %s responded with error: %s", subscriber, response["error"])
        
        if timeline:
            return OkResponse({"timeline": timeline.to_serializable()})
        else:
            return ErrorResponse(f"No available source found.")
    
    async def check_not_subscribed(self, userid):
        subscribers = await self.kademlia_connection.get_subscribers(userid)
        if self.userid in subscribers:
            await self.kademlia_connection.unsubscribe(userid, [str(s) for s in subscribers])

    async def handle_public_get(self, userid, max_posts):
        if userid != self.userid and userid not in self.subscriptions.subscriptions:
            # This node is not subscribed, so it is strange to receive a request
            # Because of this, it will check the subscription value in the DHT
            asyncio.create_task(self.check_not_subscribed(userid))
            return ErrorResponse(f"Not locally available.")

        timeline = await self.get_local(userid, max_posts)
        if timeline is None:
            return ErrorResponse(f"Not locally available.")
        return OkResponse({"timeline": timeline.to_serializable()})

    async def handle_get(self, userid, max_posts):
        timeline = await self.get_local(userid, max_posts)
        if timeline is not None:
            return OkResponse({"timeline": timeline.to_serializable()})
        response = await self.get_peers(userid, max_posts)
        return response

    async def handle_post(self, content):
        post = None
        try:
            post = self.timeline.add_post(content, self.next_post_id.get_and_advance())
            self.timeline.store(self.storage)
            self.next_post_id.store(self.storage)
            return OkResponse()
        except Exception as e:
            if post is not None:
                self.timeline.remove_post(post)
                self.next_post_id.rollback()
            log.error("Could not post message.", e)
            return ErrorResponse("Could not post message.")

    async def handle_remove(self, post_id):
        if not self.timeline.remove_post_by_id(post_id):
            return ErrorResponse("Post not found.")
        self.timeline.store(self.storage)
        return OkResponse()

    async def handle_sub(self, userid):
        if userid == self.userid:
            return ErrorResponse("Cannot subscribe to self.")

        subscriptions_backup = self.subscriptions.subscriptions.copy()

        try:
            if not self.subscriptions.subscribe(userid):
                return ErrorResponse("Already subscribed.")
            self.subscriptions.store(self.storage)
            await self.kademlia_connection.subscribe(
                userid, self.subscriptions.to_serializable()
            )
            asyncio.create_task(self.update_cached_timeline(userid))
            return OkResponse()
        except Exception as e:
            self.subscriptions.subscriptions = subscriptions_backup
            log.error("Could not subscribe.", e)
            return ErrorResponse("Could not subscribe.")

    async def handle_unsub(self, userid):
        if userid == self.userid:
            return ErrorResponse("Cannot unsubscribe from self.")

        subscriptions_backup = self.subscriptions.subscriptions.copy()
        try:
            if not self.subscriptions.unsubscribe(userid):
                return ErrorResponse("Not subscribed.")
            Timeline.delete(self.storage, userid)
            self.subscriptions.store(self.storage)
            await self.kademlia_connection.unsubscribe(
                userid, self.subscriptions.to_serializable()
            )
            return OkResponse()
        except Exception as e:
            self.subscriptions.subscriptions = subscriptions_backup
            log.error("Could not unsubscribe.", e)
            return ErrorResponse("Could not unsubscribe.")

    async def handle_view(self, max_posts):
        timelines = [self.timeline]
        warnings = []

        for subscription in self.subscriptions.subscriptions:
            response = await self.handle_get(subscription, max_posts=None)

            if response.status == "ok":
                timelines.append(Timeline.from_serializable(response.data["timeline"]))
            else:
                warnings.append({"message": response.data["error"], "subscription": str(subscription)})

        return OkResponse(
            {
                "timeline": MergedTimeline.from_timelines(
                    timelines, max_posts
                ).to_serializable(),
                "warnings": warnings,
            }
        )

    async def handle_people_i_may_know(self, max_users):
        suggestions = set()
        subscribed_by = {}

        for subscription in self.subscriptions.to_serializable():
            current_subscriptions = await self.kademlia_connection.get_subscribed(subscription)

            for sub in current_subscriptions:
                if sub == self.userid:
                    continue

                sub = str(sub)

                if sub in self.subscriptions.to_serializable():
                    continue

                suggestions.add(sub)

                if sub in subscribed_by.keys():
                    subscribed_by[sub].add(subscription)
                else:
                    subscribed_by[sub] = {subscription}

        response = [{"userid": s, "subscribed-by": list(subscribed_by[s])} for s in suggestions]

        response.sort(key=lambda x: len(x["subscribed-by"]), reverse=True)

        response = {"users": response if max_users is None else response[:max_users]}

        return OkResponse(response)

    async def update_cached_timeline(self, userid):
        subscribers = await self.kademlia_connection.get_subscribers(userid)
        if self.userid not in subscribers:
            await self.kademlia_connection.subscribe(userid, [str(s) for s in subscribers])
        else:
            await self.kademlia_connection.republish(userid)

        last_updated = None
        if Timeline.exists(self.storage, userid):
            try:
                timeline = Timeline.read(self.storage, userid)
                if timeline.is_valid():
                    last_updated = timeline.last_updated
                else:
                    Timeline.delete(self.storage, userid)
            except Exception as e:
                log.debug("Could not read cached timeline for %s: %s", userid, e)
        
        response = await self.get_peers(
            userid,
            self.max_cached_posts,
            subscribers=subscribers,
            last_updated_after=last_updated,
        )

        if response.status == "ok":
            try:
                Timeline.from_serializable(response.data["timeline"]).store(
                    self.storage
                )
                log.debug("Updated cached timeline for %s", userid)
            except Exception as e:
                log.debug("Could not update cached timeline for %s: %s", userid, e)

    async def run(
        self, port, bootstrap_nodes, local_port, cache_frequency, time_to_live, max_cached_posts
    ):
        await self.kademlia_connection.start(port, bootstrap_nodes)
        asyncio.create_task(self.local_connection.start(local_port))
        asyncio.create_task(self.public_connection.start(self.userid))

        self.max_cached_posts = max_cached_posts
        self.time_to_live = time_to_live

        while True:
            for subscription in self.subscriptions.subscriptions:
                asyncio.create_task(self.update_cached_timeline(subscription))
            await asyncio.sleep(cache_frequency)
