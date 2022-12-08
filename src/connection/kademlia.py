"""Handles and abstracts the connection to the kademlia DHT network."""
from src.validator import IpPortValidator
import asyncio
import random
import logging
import json
from kademlia.network import Server

log = logging.getLogger('timeline')

class KademliaConnection:
    BACKOFF_RATE = 1.5
    BACKOFF_MIN_RANDOM_WAIT_S = 0.2
    BACKOFF_MAX_RANDOM_WAIT_S = 1.0
    MAX_BACKOFF_S = 10 # TODO: maybe this should be configured alongside cache period

    def __init__(self, username):
        self.connection = None
        self.username = username
    
    async def subscribe(self, username, subscriptions):
        # This node owns this key. It can just set the value without worries.
        await self.put(f"{username}-subscribed", subscriptions)

        # This key is shared, so the logic is more complicated
        await self.set_subscription(f"{username}-subscribers", self.username, True)
    
    async def unsubscribe(self, username, subscriptions):
        # This node owns this key. It can just set the value without worries.
        await self.put(f"{username}-subscribed", subscriptions)

        # This key is shared, so the logic is more complicated
        await self.set_subscription(f"{username}-subscribers", self.username, False)

    async def get_subscribers(self, username):
        response = self.get(f"{username}-subscribers")
        if response is None:
            return []
        
        return [IpPortValidator().ip_address(s) for s in response]
    
    async def get_subscribed(self, username):
        response = self.get(f"{username}-subscribed")
        if response is None:
            return []
        
        return [IpPortValidator().ip_address(s) for s in response]
    
    async def set_subscription(self, key, target, subscribed):
        # Exponential backoff and multiple tries to minimize concurrency issues
        subscription = str(target)
        response = await self.get(key)
        if response is None:
            response = []

        n = -1
        while (True):
            n += 1
            log.debug(f"{n} - {response}") # TODO remove
            # Update the value
            if subscribed:
                if subscription not in response:
                    response.append(subscription)
                    await self.put(key, response)
                    log.debug(f"{n} - put {response}") # TODO remove
                else:
                    break
            else:
                if subscription in response:
                    response.remove(subscription)
                    await self.put(key, response)
                    log.debug(f"{n} - put {response}") # TODO remove
                else:
                    break

            # Exponential backoff
            backoff = min(KademliaConnection.BACKOFF_RATE**n, KademliaConnection.MAX_BACKOFF_S)
            backoff += random.uniform(KademliaConnection.BACKOFF_MIN_RANDOM_WAIT_S, KademliaConnection.BACKOFF_MAX_RANDOM_WAIT_S)

            log.debug("Waiting %s seconds before checking for concurrency issues", backoff)
            await asyncio.sleep(backoff)

            # Check if the value has changed in the meantime
            updated_response = await self.get(key)
            log.debug(f"{n} - updated: {updated_response}") # TODO remove
            if updated_response is None:
                log.debug("updated response is none") # TODO remove
                updated_response = []

            if subscribed:
                if subscription in updated_response:
                    log.debug("No concurrency issues detected")
                    break
                else:
                    log.debug("Concurrency issue detected, trying again")
                    response = updated_response
            else:
                if subscription not in updated_response:
                    log.debug("No concurrency issues detected")
                    break
                else:
                    log.debug("Concurrency issue detected, trying again")
                    response = updated_response

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
