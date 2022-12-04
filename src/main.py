import argparse
from multiprocessing.sharedctypes import Value
import sys
from src.node import Node
from src.operation import get, post, sub, unsub
from src.validator import IpPortValidator, PortValidator, IpValidator
import logging
import asyncio

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log = logging.getLogger('timeline')
log.addHandler(handler)

DEFAULT_PUBLIC_PORT = 8000
DEFAULT_KADEMLIA_PORT = 8468
DEFAULT_LOCAL_PORT = 8600

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

    start_parser.add_argument("-u", "--username", help="Username, composed of the node's IP and public port.", type=IpPortValidator(DEFAULT_PUBLIC_PORT).ip_address, required=True)
    start_parser.add_argument("-k", "--kademlia-port", help="Kademlia port number to serve at.", type=PortValidator.port, default=DEFAULT_KADEMLIA_PORT)
    start_parser.add_argument("-b", "--bootstrap-nodes", help="IP addresses of existing nodes.", type=IpPortValidator(DEFAULT_KADEMLIA_PORT).ip_address, nargs='+', default=[])

    post_parser.add_argument("filepath", help="Path to file to post.", required=True)
    get_parser.add_argument("username", help="ID of user to get timeline of.", type=IpPortValidator(DEFAULT_PUBLIC_PORT).ip_address, required=True)
    sub_parser.add_argument("username", help="ID of user to subscribe to.", type=IpPortValidator(DEFAULT_PUBLIC_PORT).ip_address, required=True)
    unsub_parser.add_argument("username", help="ID of user to unsubscribe from.", type=IpPortValidator(DEFAULT_PUBLIC_PORT).ip_address, required=True)

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
        run = Node(args.username).run(args.kademlia_port, args.bootstrap_nodes, local_port=args.local_port)
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
