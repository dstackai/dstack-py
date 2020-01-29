import sys
from argparse import ArgumentParser, Namespace
from getpass import getpass

from dstack.config import from_yaml_file, Profile


def config(args: Namespace):
    conf = from_yaml_file(args.use_global_settings)
    if args.list:
        print("list of available profiles:")
        for p in conf.list_profiles():
            print("\t" + p)
        return

    if args.profile is not None:
        profile = conf.get_profile(args.profile)
        token = get_token(args)
        if profile is None:
            conf.add_or_replace_profile(Profile(args.profile, token))
        elif args.force or confirm(f"Do you want to replace token for profile '{args.profile}'"):
            profile.token = token
            conf.add_or_replace_profile(profile)

    if args.remove is not None:
        if args.force or confirm(f"Do you want to delete profile '{args.remove}'"):
            conf.remove_profile(args.remove)

    conf.save()


def confirm(message: str) -> bool:
    reply = None
    while reply != "y" and reply != "n":
        reply = input(f"{message} (y/n)? ").lower().rstrip()
    return reply == "y"


def get_token(args: Namespace) -> str:
    if args.token is not None:
        return args.token
    else:
        return getpass("Token: ")


def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    config_parser = subparsers.add_parser("config", help="manage your configuration")
    config_parser.add_argument("--token",
                               help="set token for selected profile",
                               type=str,
                               nargs="?")
    config_parser.add_argument("--global",
                               help="configure global settings",
                               dest="use_global_settings",
                               action="store_true")
    config_parser.add_argument("--force",
                               help="don't ask for confirmation",
                               action="store_true")
    config_group = config_parser.add_mutually_exclusive_group()
    config_group.add_argument("--profile",
                              help="use profile or create a new one",
                              default="default",
                              type=str)
    config_group.add_argument("--remove",
                              help="remove existing profile",
                              type=str,
                              metavar="PROFILE")
    config_group.add_argument("--list",
                              help="list configured profiles",
                              action="store_true")
    config_parser.set_defaults(func=config)

    if len(sys.argv) < 2:
        parser.print_help()
        exit(1)

    args = parser.parse_args()
    args.func(args)

