import asyncio
from kademlia.network import Server

def start(port, local_port, bootstrap_ips, debug):
    # TODO start listening on local port in another future
    #      (unless there is a better alternative that I don't know of)
    server = Server()

    loop = asyncio.new_event_loop()
    loop.set_debug(debug)

    loop.run_until_complete(server.listen(port))

    if len(bootstrap_ips) > 0:
        loop.run_until_complete(server.bootstrap(bootstrap_ips))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        loop.close()
