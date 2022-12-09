"""Main script. Parses arguments and calls the appropriate function, either in src.node or in src.operation."""
import argparse
import logging
import asyncio
from src.node import Node
from src.operation import get, post, delete, sub, unsub, view, people_i_may_know
from src.validator import IpPortValidator, PortValidator, PositiveIntegerValidator, NonNegativeIntegerValidator

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log = logging.getLogger('timeline')
log.addHandler(handler)

def parse_arguments():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(required=True, dest="command")

    start_parser = subparsers.add_parser("start", description="Join network of timelines.")
    post_parser = subparsers.add_parser("post", description="Post in your timeline.")
    delete_parser = subparsers.add_parser("delete", description="Delete a post from your timeline.")
    get_parser = subparsers.add_parser("get", description="Find a user's timeline.")
    sub_parser = subparsers.add_parser("sub", description="Subscribe to a user's timeline.")
    unsub_parser = subparsers.add_parser("unsub", description="Unsubscribe to a user's timeline.")
    view_parser = subparsers.add_parser("view", description="View your feed with the posts made by you and the users you are subscribed to.")
    may_know_parser = subparsers.add_parser("people-i-may-know", description="Find people you may know based on your subscriptions.")
    all_parsers = [start_parser, post_parser, delete_parser, get_parser, sub_parser, unsub_parser, view_parser, may_know_parser]

    for subparser in all_parsers:
        # Adding command here instead of main parser so that they appear
        # in subcommand help
        subparser.add_argument("-d", "--debug", help="Debug and log to stdout.", action="store_true")

    start_parser.add_argument("userid", help="ID of the user, composed of the node's IP and public port.", type=IpPortValidator(Node.DEFAULT_PUBLIC_PORT).ip_address)
    start_parser.add_argument("-k", "--kademlia-port", help="Kademlia port number to serve at.", type=PortValidator.port, default=Node.DEFAULT_KADEMLIA_PORT)
    start_parser.add_argument("-b", "--bootstrap-nodes", help="IP addresses of existing nodes.", type=IpPortValidator(Node.DEFAULT_KADEMLIA_PORT).ip_address, nargs='+', default=[])
    start_parser.add_argument("-f", "--cache-frequency", help="The time in seconds it takes between caching periods.", type=PositiveIntegerValidator.positive_integer, default=Node.DEFAULT_SLEEP_TIME_BETWEEN_CACHING)
    start_parser.add_argument("-c", "--max-cached-posts", help="The maximum number of posts to cache per subscription.", type=PositiveIntegerValidator.positive_integer, default=Node.DEFAULT_MAX_CACHED_POSTS)

    post_parser.add_argument("filepath", help="Path to file to post.")
    get_parser.add_argument("userid", help="ID of user to get timeline of.", type=IpPortValidator(Node.DEFAULT_PUBLIC_PORT).ip_address)
    get_parser.add_argument("max_posts", help="Limit the number of posts to get.", type=PositiveIntegerValidator.positive_integer, default=None, nargs="?")
    sub_parser.add_argument("userid", help="ID of user to subscribe to.", type=IpPortValidator(Node.DEFAULT_PUBLIC_PORT).ip_address)
    unsub_parser.add_argument("userid", help="ID of user to unsubscribe from.", type=IpPortValidator(Node.DEFAULT_PUBLIC_PORT).ip_address)
    view_parser.add_argument("max_posts", help="Limit the number of posts to get.", type=PositiveIntegerValidator.positive_integer, default=None, nargs="?")
    may_know_parser.add_argument("max_users", help="Limit the number of users to get.", type=PositiveIntegerValidator.positive_integer, default=None, nargs="?")
    delete_parser.add_argument("post_id", help="ID of post to delete.", type=NonNegativeIntegerValidator.non_negative_integer)

    for subparser in all_parsers:
        # Adding command here so it appears at the end of the help
        subparser.add_argument("-l", "--local-port", help="Port number that listens for local operations.", type=PortValidator.port, default=Node.DEFAULT_LOCAL_PORT)

    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.debug:
        log.setLevel(logging.DEBUG)

    log.debug("Called with arguments: %s", args)

    if args.command == "start":
        run = Node(args.userid).run(
            args.kademlia_port,
            args.bootstrap_nodes,
            local_port=args.local_port,
            cache_frequency=args.cache_frequency,
            max_cached_posts=args.max_cached_posts
        )
    elif args.command == "get":
        run = get(args.userid, local_port=args.local_port, max_posts=args.max_posts)
    elif args.command == "post":
        run = post(args.filepath, local_port=args.local_port)
    elif args.command == "delete":
        run = delete(args.post_id, local_port=args.local_port)
    elif args.command == "sub":
        run = sub(args.userid, local_port=args.local_port)
    elif args.command == "unsub":
        run = unsub(args.userid, local_port=args.local_port)
    elif args.command == "view":
        run = view(local_port=args.local_port, max_posts=args.max_posts)
    elif args.command == "people-i-may-know":
        run = people_i_may_know(None, local_port=args.local_port, max_users=args.max_users)
    
    asyncio.run(run, debug=args.debug)

if __name__ == "__main__":
    main()
