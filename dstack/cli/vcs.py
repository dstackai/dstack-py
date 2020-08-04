from argparse import Namespace
from pathlib import Path
from typing import List, Dict, Optional

from dstack import create_context
from dstack.vcs.fs import FileSystem, Query


def parse_meta(metadata: Optional[List[str]]) -> Optional[Dict[str, str]]:
    if not metadata:
        return None

    result = {}

    for meta in metadata:
        if "=" in meta:
            k, v = meta.split("=")
            result[k] = v
        else:
            result[meta] = "true"

    return result


def add(args: Namespace):
    fs = FileSystem(Path("."))
    fs.add([Path(path) for path in args.files], parse_meta(args.meta))


def init(args: Namespace):
    context = create_context(args.stack, args.profile)
    fs = FileSystem(Path("."))
    fs.init(context)


def checkout(args: Namespace):
    context = create_context(args.stack, args.profile)
    fs = FileSystem(Path(args.path))
    fs.checkout(context)


def fetch(args: Namespace):
    fs = FileSystem(Path("."))
    fs.fetch()


def pull(args: Namespace):
    fs = FileSystem(Path("."))
    if args.query:
        fs.pull(query=Query(args.query), force=args.force)
    else:
        fs.pull(force=args.force)


def push(args: Namespace):
    fs = FileSystem(Path("."))
    fs.push()


def status(args: Namespace):
    fs = FileSystem(Path("."))
    for attr in fs.list():
        state = " "
        path = Path(attr.path)
        if attr.hash_code:
            if not path.exists():
                state = "-"
            elif attr.hash_code != fs.attributes(attr.path).hash_code:
                state = "*"
        else:
            state = "+"
        print(f"{state}{attr.path}")


def register_parsers(main_subparsers):
    parser = main_subparsers.add_parser("vcs", help="version control system")
    subparsers = parser.add_subparsers()

    add_parser = subparsers.add_parser("add", help="add files to index")
    add_parser.add_argument("files", metavar="FILE", help="file to add", nargs="+")
    add_parser.add_argument("--meta", help="provide metadata", nargs="*")
    add_parser.set_defaults(func=add)

    init_parser = subparsers.add_parser("init", help="initialize a new stack")
    init_parser.add_argument("stack", metavar="STACK", help="stack name")
    init_parser.add_argument("--profile", type=str, default="default")
    init_parser.set_defaults(func=init)

    checkout_parser = subparsers.add_parser("checkout", help="checkout a stack to specified location")
    checkout_parser.add_argument("stack", metavar="STACK", help="stack name")
    checkout_parser.add_argument("path", metavar="PATH", help="location")
    checkout_parser.add_argument("--profile", type=str, default="default")
    checkout_parser.set_defaults(func=checkout)

    fetch_parser = subparsers.add_parser("fetch", help="fetch metadata")
    fetch_parser.set_defaults(func=fetch)

    pull_parser = subparsers.add_parser("pull", help="fetch files from server")
    pull_parser.add_argument("--query", help="query to selective fetch")
    pull_parser.add_argument("--force", help="override files in the case of conflict", action="store_true")
    pull_parser.set_defaults(func=pull)

    push_parser = subparsers.add_parser("push", help="push changed files to server")
    push_parser.set_defaults(func=push)

    push_parser = subparsers.add_parser("status", help="show the working tree status")
    push_parser.set_defaults(func=status)
