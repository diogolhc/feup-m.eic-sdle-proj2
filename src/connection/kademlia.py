from src.validator import IpPortValidator
import logging
import json
from kademlia.network import Server

log = logging.getLogger('timeline')

class KademliaConnection:
    def __init__(self, username):
        self.connection = None
        self.username = username
    
    async def subscribe(self, username):
        await self.set_subscription(f"{username}-subscribed", username, True)
        await self.set_subscription(f"{username}-subscribers", self.username, True)
    
    async def unsubscribe(self, username):
        await self.set_subscription(f"{username}-subscribed", username, False)
        await self.set_subscription(f"{username}-subscribers", self.username, False)

    async def get_subscribers(self, username):
        response = self.get_subscribers_raw(username)
        if response is None:
            return []
        
        return [IpPortValidator().ip_address(s) for s in response]
    
    async def set_subscription(self, key, target, subscribed):
        response = self.get(key)
        if response is None:
            response = []
        subscription = str(target)

        if subscribed:
            if subscription not in response:
                response.append(subscription)
                self.put(key, response)
        else:
            if subscription in response:
                response.remove(subscription)
                self.put(key, response)
        # TODO this can cause concurrency issues, we should try to minimize them, for example with exponential backoff and multiple tries
        #      Probably this concurrency problem will only happen in ip:port-subscribers, since that is shared among many people
        #      The key ip:port-subscribed is owned by a single person, and no one else will edit it

    async def get(self, key):
        response = await self.connection.get(key)
        if response is None:
            return None
        return json.loads(response)
    
    async def put(self, key, value):
        await self.connection.set(key, json.dumps(value))

    async def start(self, port, bootstrap_nodes):
        self.connection = Server()

        await self.connection.listen(port)
        
        if len(bootstrap_nodes) > 0:
            log.debug("Bootstrapping with %s", bootstrap_nodes)
            await self.connection.bootstrap(bootstrap_nodes)
        
        log.debug("Ready to listen to peers on port %s", port)
