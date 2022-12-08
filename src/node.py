"""Class for the node that runs the timeline service."""
import asyncio
import logging
from src.data.timeline import Timeline
from src.data.merged_timeline import MergedTimeline
from src.data.subscriptions import Subscriptions
from src.data.storage import PersistentStorage
from src.connection import (
    request,
    LocalConnection,
    PublicConnection,
    KademliaConnection,
    OkResponse,
    ErrorResponse,
)
from src.data.username import Username

log = logging.getLogger("timeline")


class Node:
    DEFAULT_SLEEP_TIME_BETWEEN_CACHING = 10
    DEFAULT_MAX_CACHED_POSTS = 10
    DEFAULT_PUBLIC_PORT = 8000
    DEFAULT_KADEMLIA_PORT = 8468
    DEFAULT_LOCAL_PORT = 8600

    def __init__(self, username):
        self.username = Username(username)

        # Connections
        self.kademlia_connection = KademliaConnection(self.username)
        self.local_connection = LocalConnection(
            self.handle_get, self.handle_post, self.handle_sub, self.handle_unsub, self.handle_view, self.handle_people_i_may_know
        )
        self.public_connection = PublicConnection(self.handle_public_get)

        # Storage
        self.storage = PersistentStorage(self.username)
        self.storage.create_dir(Timeline.TIMELINES_FOLDER)

        try:
            self.timeline = Timeline.read(self.storage, self.username)
        except Exception as e:
            print("Could not read timeline from storage.", e)
            exit(1)

        try:
            self.subscriptions = Subscriptions.read(self.storage)
        except Exception as e:
            print("Could not read subscriptions from storage.", e)
            exit(1)
    
    async def get_local(self, username, max_posts):
        # 1st try: get own timeline
        if username == self.username:
            return self.timeline.cache(max_posts)

        # 2nd try: get cached timeline
        # TODO we might want this to be done only after step 3 (if the caller was handle_get())? i don't know
        if Timeline.exists(self.storage, username):
            try:
                timeline = Timeline.read(self.storage, username)
                if timeline.is_valid():
                    return timeline.cache(max_posts)
                    
            except Exception as e:
                print("Could not read timeline from storage.", e)
        
        return None
    
    async def get_peers(self, username, max_posts, subscribers=None, last_updated_after=None):
        # 3rd try: get timeline directly from owner
        data = {
            "command": "get-timeline",
            "username": str(username),
            "max-posts": max_posts,
        }

        log.debug("Connecting to %s", username)
        response = await request(data, username.ip, username.port)

        if response["status"] == "ok":
            return OkResponse({"timeline": response["timeline"]})

        # 4th try: get timeline from a subscriber
        if subscribers is None:
            subscribers = await self.kademlia_connection.get_subscribers(username)
            if subscribers is None:
                return ErrorResponse(f"No available source found.")

        for subscriber in subscribers:
            log.debug("Connecting to subscriber %s:%s", subscriber[0], subscriber[1])
            response = await request(data, subscriber[0], subscriber[1])
            if response["status"] == "ok":
                timeline = Timeline.from_serializable(response["timeline"])
                if timeline.last_updated <= last_updated_after:
                    continue # The timeline is older than the current one

                # TODO the teacher suggested that instead of just returning this one,
                #      we could have some heuristic probability of trying others until
                #      we are confident that we have an updated enough timeline.
                return OkResponse({"timeline": response["timeline"]})
            else:
                log.debug(
                    "Subscriber %s:%s responded with error: %s",
                    subscriber[0],
                    subscriber[1],
                    response["error"],
                )

        return ErrorResponse(f"No available source found.")
    
    async def check_not_subscribed(self, username):
        subscribers = await self.kademlia_connection.get_subscribers(username)
        if self.username in subscribers:
            await self.kademlia_connection.unsubscribe(username, subscribers)
        
    async def handle_public_get(self, username, max_posts):
        if username != self.username and username not in self.subscriptions.subscriptions:
            # This node is not subscribed, so it is strange to receive a request
            # Because of this, it will check the subscription value in the DHT
            asyncio.create_task(self.check_not_subscribed(username))
            return ErrorResponse(f"Not locally available.")            
        
        timeline = await self.get_local(username, max_posts)
        if timeline is None:
            return ErrorResponse(f"Not locally available.")
        return OkResponse(
            {"timeline": timeline.to_serializable()}
        )

    async def handle_get(self, username, max_posts):
        timeline = await self.get_local(username, max_posts)
        if timeline is not None:
            return OkResponse(
                {"timeline": timeline.to_serializable()}
            )
        return await self.get_peers(username, max_posts)

    async def handle_post(self, filepath):
        post = None
        try:
            with open(filepath, "r") as f:
                post = self.timeline.add_post(f.read())
            self.timeline.store(self.storage)
            return OkResponse()
        except Exception as e:
            if post is not None:
                self.timeline.remove_post(post)
            print("Could not post message.", e)
            return ErrorResponse("Could not post message.")

    async def handle_sub(self, username):
        if username == self.username:
            return ErrorResponse("Cannot subscribe to self.")
        
        subscriptions_backup = self.subscriptions.subscriptions.copy()
        
        try:
            if not self.subscriptions.subscribe(username):
                return ErrorResponse("Already subscribed.")
            self.subscriptions.store(self.storage)
            await self.kademlia_connection.subscribe(username, self.subscriptions.to_serializable())
            asyncio.create_task(self.update_cached_timeline(username))
            return OkResponse()
        except Exception as e:
            self.subscriptions.subscriptions = subscriptions_backup
            print("Could not subscribe.", e)
            return ErrorResponse("Could not subscribe.")

    async def handle_unsub(self, username):
        if username == self.username:
            return ErrorResponse("Cannot unsubscribe from self.")
        
        subscriptions_backup = self.subscriptions.subscriptions.copy()
        try:
            if not self.subscriptions.unsubscribe(username):
                return ErrorResponse("Not subscribed.")
            Timeline.delete(self.storage, username)
            self.subscriptions.store(self.storage)
            await self.kademlia_connection.unsubscribe(username, self.subscriptions.to_serializable())
            return OkResponse()
        except Exception as e:
            self.subscriptions.subscriptions = subscriptions_backup
            print("Could not unsubscribe.", e)
            return ErrorResponse("Could not unsubscribe.")

    async def handle_view(self, max_posts):
        timelines = [self.timeline]
        warnings = []

        for subscription in self.subscriptions.to_serializable():
            response = self.handle_get(subscription, max_posts=None)

            if response["status"] == "ok":
                timelines.append(response["timeline"])
            else:
                warnings.append(response["error"] + "-" + subscription)

        return OkResponse({"timeline": MergedTimeline(timelines, max_posts), "warnings": warnings})

    async def handle_people_i_may_know(self, max_users):
        suggestions = set()
        common = {}

        for subscription in self.subscriptions.to_serializable():
            subscriptions = await self.kademlia_connection.get_subscribed(subscription)

            suggestions.update(subscriptions)

            for sub in subscriptions:
                if sub in common.keys():
                    common[sub].add(subscription)
                else:
                    common[sub] = {subscription}

        response = [{"username": s, "common": common[s]} for s in suggestions]

        response.sort(key=lambda x: len(x["common"]), reverse=True)

        response = response if max_users is None else response[:max_users]

        return OkResponse(response)            

    async def update_cached_timeline(self, username):
        subscribers = await self.kademlia_connection.get_subscribers(username)
        if self.username not in subscribers:
            await self.kademlia_connection.subscribe(username, subscribers)
        
        last_updated = None
        if Timeline.exists(self.storage, username):
            try:
                last_updated = Timeline.read(self.storage, username).last_updated
            except Exception as e:
                log.debug("Could not read cached timeline for %s: %s", username, e)
        response = await self.get_peers(username, self.max_cached_posts, subscribers=subscribers, last_updated_after=last_updated)
        if response.status == "ok":
            try:
                Timeline.from_serializable(response.data["timeline"]).store(self.storage)
                log.debug("Updated cached timeline for %s", username)
            except Exception as e:
                log.debug("Could not update cached timeline for %s: %s", username, e)
        else:
            log.debug("Could not update cached timeline for %s: %s", username, response.error)

    async def run(self, port, bootstrap_nodes, local_port, cache_frequency, max_cached_posts):
        # TODO the teacher talked about synchronizing clocks between nodes, but I don't know why that would be necessary in this project.
        #      anyway, if we decide to do that, it should be done only after everything else is done, probably.
        await self.kademlia_connection.start(port, bootstrap_nodes)
        asyncio.create_task(self.local_connection.start(local_port))
        asyncio.create_task(self.public_connection.start(self.username))

        self.max_cached_posts = max_cached_posts
        while True:
            for subscription in self.subscriptions.subscriptions:
                asyncio.create_task(self.update_cached_timeline(subscription, max_cached_posts))
            await asyncio.sleep(cache_frequency)
