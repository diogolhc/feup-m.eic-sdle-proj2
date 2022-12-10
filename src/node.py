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
            self.handle_people_i_may_know,
            self.handle_get_subscribers
        )
        self.public_connection = PublicConnection(self.handle_public_get)

        # Storage
        self.storage = PersistentStorage(self.userid)
        self.storage.create_dir(Timeline.TIMELINES_FOLDER)

        try:
            self.timeline = Timeline.read(self.storage, self.userid)
        except Exception as e:
            print("Could not read timeline from storage.", e)
            exit(1)

        try:
            self.subscriptions = Subscriptions.read(self.storage)
        except Exception as e:
            print("Could not read subscriptions from storage.", e)
            exit(1)

        try:
            self.next_post_id = NextPostId.read(self.storage)
        except Exception as e:
            print("Could not read next post id from storage.", e)
            exit(1)

    async def get_local(self, userid, max_posts):
        # 1st try: get own timeline
        if userid == self.userid:
            log.debug("Getting own timeline")
            return self.timeline.cache(max_posts)

        # 2nd try: get cached timeline
        # TODO we might want this to be done only after step 3 (if the caller was handle_get())? i don't know
        log.debug("Check if cached")
        if Timeline.exists(self.storage, userid):
            log.debug("Getting cached timeline")
            try:
                timeline = Timeline.read(self.storage, userid)
                if timeline.is_valid():
                    log.debug("Returned cached timeline")
                    return timeline.cache(max_posts)

            except Exception as e:
                print("Could not read timeline from storage.", e)

        return None

    async def get_peers(
        self, userid, max_posts, subscribers=None, last_updated_after=None
    ):
        # TODO if we are subscribed to userid, maybe we can update our cache with the result of this function?
        # 3rd try: get timeline directly from owner
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
            message = ("Could not connect to %s", userid)
            log.debug(message)
            print(message)

        # 4th try: get timeline from a subscriber
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
            print("Could not post message.", e)
            return ErrorResponse("Could not post message.")

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
            print("Could not subscribe.", e)
            return ErrorResponse("Could not subscribe.")
    
    async def handle_remove(self, post_id):
        if not self.timeline.remove_post_by_id(post_id):
            return ErrorResponse("Post not found.")
        self.timeline.store(self.storage)
        return OkResponse()

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
            print("Could not unsubscribe.", e)
            return ErrorResponse("Could not unsubscribe.")

    async def handle_view(self, max_posts):
        timelines = [self.timeline]
        warnings = []

        for subscription in self.subscriptions.subscriptions:
            response = await self.handle_get(subscription, max_posts=None)

            if response.status == "ok":
                timelines.append(Timeline.from_serializable(response.data["timeline"]))
            else:
                warnings.append(response.data["error"] + "-" + subscription)

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
        common = {}

        for subscription in self.subscriptions.to_serializable():
            #print("SUB = " + str(subscription))
            #print("\nIN FOR\n")
            current_subscriptions = await self.kademlia_connection.get_subscribed(subscription)

            #print("\nSIZE OF SUBSCRIPTIONS: " + str(len(current_subscriptions)) + "\n")

            for sub in current_subscriptions:
                #print("FRIEND OF SUB = " + str(sub))
                #print("ME = " + str(self.userid))

                if sub == self.userid:
                    #print("\nself\n")
                    continue

                sub = str(sub)

                if sub in self.subscriptions.to_serializable():
                    #print("ALREADY IN SUBS")
                    continue

                suggestions.add(sub)

                #print("\nCOMMON KEYS:")
                #print(common.keys())

                if sub in common.keys():
                    common[sub].add(subscription)
                else:
                    common[sub] = {subscription}

        response = []
        response = [{"userid": s, "common": list(common[s])} for s in suggestions]

        response.sort(key=lambda x: len(x["common"]), reverse=True)

        #print("\n\nRESPONSE = ")
        #print(response)
        #print("\n\n")

        r = {"users": response if max_users is None else response[:max_users]}

        #print("\n\nREAL RESPONSE = ")
        #print(r)

        return OkResponse(r)

    async def handle_get_subscribers(self, userid):
        return OkResponse({"subscribers": [str(s) for s in await self.kademlia_connection.get_subscribers(userid)]})

    async def update_cached_timeline(self, userid):
        subscribers = await self.kademlia_connection.get_subscribers(userid)
        if self.userid not in subscribers:
            await self.kademlia_connection.subscribe(userid, [str(s) for s in subscribers])
        else:
            await self.kademlia_connection.republish(userid)

        last_updated = None
        if Timeline.exists(self.storage, userid):
            try:
                last_updated = Timeline.read(self.storage, userid).last_updated
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
        self, port, bootstrap_nodes, local_port, cache_frequency, max_cached_posts
    ):
        await self.kademlia_connection.start(port, bootstrap_nodes)
        asyncio.create_task(self.local_connection.start(local_port))
        asyncio.create_task(self.public_connection.start(self.userid))

        self.max_cached_posts = max_cached_posts
        while True:
            for subscription in self.subscriptions.subscriptions:
                asyncio.create_task(self.update_cached_timeline(subscription))
            await asyncio.sleep(cache_frequency)
