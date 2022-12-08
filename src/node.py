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
from src.data.user import User

log = logging.getLogger("timeline")


class Node:
    DEFAULT_SLEEP_TIME_BETWEEN_CACHING = 10
    DEFAULT_MAX_CACHED_POSTS = 10
    DEFAULT_PUBLIC_PORT = 8000
    DEFAULT_KADEMLIA_PORT = 8468
    DEFAULT_LOCAL_PORT = 8600

    def __init__(self, userid):
        self.userid = User(userid)

        # Connections
        self.kademlia_connection = KademliaConnection(self.userid)
        self.local_connection = LocalConnection(
            self.handle_get,
            self.handle_post,
            self.handle_sub,
            self.handle_unsub,
            self.handle_view,
            self.handle_people_i_may_know,
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

    async def get_local(self, userid, max_posts):
        # 1st try: get own timeline
        if userid == self.userid:
            return self.timeline.cache(max_posts)

        # 2nd try: get cached timeline
        # TODO we might want this to be done only after step 3 (if the caller was handle_get())? i don't know
        if Timeline.exists(self.storage, userid):
            try:
                timeline = Timeline.read(self.storage, userid)
                if timeline.is_valid():
                    return timeline.cache(max_posts)

            except Exception as e:
                print("Could not read timeline from storage.", e)

        return None

    async def get_peers(
        self, userid, max_posts, subscribers=None, last_updated_after=None
    ):
        # 3rd try: get timeline directly from owner
        data = {
            "command": "get-timeline",
            "userid": str(userid),
            "max-posts": max_posts,
        }

        log.debug("Connecting to %s", userid)
        response = await request(data, userid.ip, userid.port)

        if response["status"] == "ok":
            return OkResponse({"timeline": response["timeline"]})

        # 4th try: get timeline from a subscriber
        if subscribers is None:
            subscribers = await self.kademlia_connection.get_subscribers(userid)
            if subscribers is None:
                return ErrorResponse(f"No available source found.")

        for subscriber in subscribers:
            log.debug("Connecting to subscriber %s:%s", subscriber.ip, subscriber.port)
            response = await request(data, subscriber.ip, subscriber.port)
            if response["status"] == "ok":
                timeline = Timeline.from_serializable(response["timeline"])
                if timeline.last_updated <= last_updated_after:
                    continue  # The timeline is older than the current one

                # TODO the teacher suggested that instead of just returning this one,
                #      we could have some heuristic probability of trying others until
                #      we are confident that we have an updated enough timeline.
                return OkResponse({"timeline": response["timeline"]})
            else:
                log.debug(
                    "Subscriber %s:%s responded with error: %s",
                    subscriber.ip,
                    subscriber.port,
                    response["error"],
                )

        return ErrorResponse(f"No available source found.")

    async def check_not_subscribed(self, userid):
        subscribers = await self.kademlia_connection.get_subscribers(userid)
        if self.userid in subscribers:
            await self.kademlia_connection.unsubscribe(userid, subscribers)

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
        return await self.get_peers(userid, max_posts)

    async def handle_post(self, content):
        post = None
        try:
            post = self.timeline.add_post(content)
            self.timeline.store(self.storage)
            return OkResponse()
        except Exception as e:
            if post is not None:
                self.timeline.remove_post(post)
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

                if sub is self.userid:
                    #print("\nself\n")
                    continue

                sub = str(sub)

                if sub in self.subscriptions.to_serializable():
                    #print("ALREADY IN SUBS")
                    continue

                suggestions.add(sub)

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

    async def update_cached_timeline(self, userid):
        subscribers = await self.kademlia_connection.get_subscribers(userid)
        if self.userid not in subscribers:
            await self.kademlia_connection.subscribe(userid, subscribers)

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
        else:
            log.debug(
                "Could not update cached timeline for %s: %s",
                userid,
                response.data["error"],
            )

    async def run(
        self, port, bootstrap_nodes, local_port, cache_frequency, max_cached_posts
    ):
        # TODO the teacher talked about synchronizing clocks between nodes, but I don't know why that would be necessary in this project.
        #      anyway, if we decide to do that, it should be done only after everything else is done, probably.
        await self.kademlia_connection.start(port, bootstrap_nodes)
        asyncio.create_task(self.local_connection.start(local_port))
        asyncio.create_task(self.public_connection.start(self.userid))

        self.max_cached_posts = max_cached_posts
        while True:
            for subscription in self.subscriptions.subscriptions:
                asyncio.create_task(self.update_cached_timeline(subscription))
            await asyncio.sleep(cache_frequency)
