import asyncio
import logging
from src.timeline import Timeline
from src.storage import PersistentStorage
from src.connection import request, LocalConnection, PublicConnection, KademliaConnection, OkResponse, ErrorResponse

log = logging.getLogger('timeline')

class Node:
    SLEEP_TIME_BETWEEN_CACHING = 10

    def __init__(self, username):
        self.username = username
        self.kademlia_connection = KademliaConnection(self.username)
        self.local_connection = LocalConnection(self.handle_get, self.handle_post, self.handle_sub, self.handle_unsub)
        self.public_connection = PublicConnection(self.handle_public_get)
        self.storage = PersistentStorage(self.username)
        try:
            self.timeline = Timeline.read(self.storage)
        except ... as e:
            print("Could not read timeline from storage.", e)
            exit(1)
    
    async def handle_public_get(self, username, max_posts):
        # 1st try: get own timeline
        if username == self.username:
            return OkResponse({"timeline": self.timeline.cache(max_posts)})

        # 2nd try: get cached timeline
        if self.storage.exists(username):
            try:
                timeline = Timeline.read(self.storage, username)
                # TODO check if timeline is up to date/valid
                return OkResponse({"timeline": timeline.cache(max_posts)})
            except ... as e:
                print("Could not read timeline from storage.", e)
        
        return ErrorResponse(f"Not locally available.")
    
    async def handle_get(self, username, max_posts):
        # 1st and 2nd try: locally available
        response = await self.handle_public_get(username, max_posts)
        if response["status"] == "ok":
            return response

        # 3rd try: get timeline directly from owner
        data = {
            "command": "get-timeline", 
            "username": f"{username[0]}:{username[1]}",
            "max_posts": max_posts,
        }

        log.debug("Connecting to %s server on port %s", username[0], username[1])
        response = await request(data, username[0], username[1])

        if response["status"] == "ok":
            return OkResponse({ "timeline": response["timeline"] })

        # 4th try: get timeline from a subscriber
        subscribers = await self.kademlia_get_subscribers(username)
        if subscribers is None:
            return ErrorResponse(f"No available source found.")
        
        for subscriber in subscribers:
            log.debug("Connecting to subscriber %s:%s", subscriber[0], subscriber[1])
            response = await request(data, subscriber[0], subscriber[1])
            if response["status"] == "ok":
                # TODO the teacher suggested that instead of just returning this one, 
                #      we could have some heuristic probability of trying others until 
                #      we are confident that we have an updated enough timeline.
                return OkResponse({ "timeline": response["timeline"] })
            else:
                log.debug("Subscriber %s:%s responded with error: %s", subscriber[0], subscriber[1], response["error"])

        return ErrorResponse(f"No available source found.")
    
    async def handle_post(self, filepath):
        try:
            with open(filepath, "r") as f:
                this.timeline.add_post(f.read())
            this.timeline.store(self.storage)
            return OkResponse()
        except ... as e:
            print("Could not post message.", e)
            return ErrorResponse("Could not post message.")
    
    async def handle_sub(self, username):
        # TODO we need to set an async function (self.update_cached_timelines) that periodically goes to every subscriber and asks for the latest timeline
        #      in order to cache it. The first time should be before subscribing probably, but then it's just periodic.
        self.kademlia_connection.subscribe(username)
        return OkResponse()

    async def handle_unsub(self, username):
        self.kademlia_connection.unsubscribe(username)
        return OkResponse()

    async def update_cached_timelines(self):
        # TODO this is where we should go to everyone we subscribed and ask for the latest timeline
        pass

    async def run(self, port, bootstrap_nodes, local_port):
        # TODO the teacher talked about synchronizing clocks between nodes, but I don't know why that would be necessary in this project.
        #      anyway, if we decide to do that, it should be done only after everything else is done, probably.
        await self.kademlia_connection.start(port, bootstrap_nodes)
        asyncio.create_task(self.local_connection.start(local_port))
        asyncio.create_task(self.public_connection.start(self.username))

        while True:
            await self.update_cached_timelines()
            await asyncio.sleep(self.SLEEP_TIME_BETWEEN_CACHING) # TODO maybe this can be a cmd argument
