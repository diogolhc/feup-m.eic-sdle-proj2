class KademliaConnection:
    def __init__(self):
        self.connection = None
    
    async def subscribe(self, username, subscriber):
        await self.set_subscription(username, subscriber, True)
    
    async def unsubscribe(self, username, subscriber):
        await self.set_subscription(username, subscriber, False)

    async def get_subscribers(self, username):
        response = self.get_subscribers_raw(username)
        if response is None:
            return []
        
        return [IpPortValidator().ip_address(s) for s in response]
    
    async subscription_key(self, username):
        return f"{username[0]}:{username[1]}-subscribers"
    
    async def set_subscription(self, username, subscriber, subscribed):
        response = self.get(self.subscription_key(username))
        if response is None:
            response = []
        subscription = f"{subscriber[0]}:{subscriber[1]}"

        if subscribed:
            if subscription not in response:
                response.append(subscription)
                self.put(self.subscription_key(username), response)
        else:
            if subscription in response:
                response.remove(subscription)
                self.put(self.subscription_key(username), response)
        # TODO this can cause concurrency issues, we should try to minimize them, for
        #      example with exponential backoff and multiple tries

    async def get(key):
        response = await self.connection.get(key)
        if response is None:
            return None
        return json.loads(response)
    
    async def put(key, value):
        await self.connection.set(key, json.dumps(value))

    async def start(self, port, bootstrap_nodes):
        self.connection = Server()

        await self.connection.listen(port)
        
        if len(bootstrap_nodes) > 0:
            log.debug("Bootstrapping with %s", bootstrap_nodes)
            await self.connection.bootstrap(bootstrap_nodes)
        
        log.debug("Ready to listen to peers on port %s", port)
