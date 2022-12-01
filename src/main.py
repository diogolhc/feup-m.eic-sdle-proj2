import argparse
from multiprocessing.sharedctypes import Value
import sys
from node import Node
from operation import get, post, sub, unsub
import ipaddress
import logging
import asyncio

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log = logging.getLogger('timeline')
log.addHandler(handler)

DEFAULT_KADEMLIA_PORT = 8468
DEFAULT_LOCAL_PORT = 8600

class PortValidator:
    """Validates and parses a port."""
    def port(s):
        port = int(s)
        if port < 1 or port > 65535:
            raise ValueError
        return port


class IpValidator:
    def ip_address(s):
        """Validates and parses an ip address."""
        ipaddress.ip_address(s)
        return s


class IpPortValidator:
    def __init__(self, default_port=None):
        self.default_port = default_port

    def ip_address(self, s):
        """Validates and parses an ip:port pair."""
        parts = s.split(':')

        if len(parts) == 1:
            if self.default_port is None:
                raise ValueError
            port = self.default_port
        elif len(parts) == 2:
            port = PortValidator.port(parts[1])
        else:
            raise ValueError
        
        ip = IpValidator.ip_address(parts[0])

        return (ip, port)


def parse_arguments():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(required=True, dest="command")

    start_parser = subparsers.add_parser("start", description="Join network of timelines.")
    post_parser = subparsers.add_parser("post", description="Post in your timeline.")
    get_parser = subparsers.add_parser("get", description="Find a user's timeline.")
    sub_parser = subparsers.add_parser("sub", description="Subscribe to a user's timeline.")
    unsub_parser = subparsers.add_parser("unsub", description="Unsubscribe to a user's timeline.")
    all_parsers = [start_parser, post_parser, get_parser, sub_parser, unsub_parser]

    for subparser in all_parsers:
        # Adding command here instead of main parser so that they appear
        # in subcommand help
        subparser.add_argument("-d", "--debug", help="Debug and log to stdout.", action=argparse.BooleanOptionalAction)

    start_parser.add_argument("-p", "--port", help="Kademlia port number to serve at.", type=PortValidator.port, default=DEFAULT_KADEMLIA_PORT)
    start_parser.add_argument("-b", "--bootstrap-nodes", help="IP addresses of existing nodes.", type=IpPortValidator(DEFAULT_KADEMLIA_PORT).ip_address, nargs='+', default=[])

    post_parser.add_argument("filepath", help="Path to file to post.")
    get_parser.add_argument("username", help="ID of user to get timeline of.")
    sub_parser.add_argument("username", help="ID of user to subscribe to.")
    unsub_parser.add_argument("username", help="ID of user to unsubscribe from.")

    for subparser in all_parsers:
        # Adding command here so it appears at the end of the help
        subparser.add_argument("-l", "--local-port", help="Port number that listens for local operations.", type=PortValidator.port, default=DEFAULT_LOCAL_PORT)

    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.debug:
        log.setLevel(logging.DEBUG)

    log.debug("Called with arguments: %s", args)

    if args.command == "start":
        run = Node().run(args.port, args.bootstrap_nodes, local_port=args.local_port)
    elif args.command == "get":
        run = get(args.username, local_port=args.local_port)
    elif args.command == "post":
        run = post(args.filepath, local_port=args.local_port)
    elif args.command == "sub":
        run = sub(args.username, local_port=args.local_port)
    elif args.command == "unsub":
        run = unsub(args.username, local_port=args.local_port)
    
    asyncio.run(run, debug=args.debug)

if __name__ == "__main__":
    main()
