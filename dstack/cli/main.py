import sys
from argparse import ArgumentParser, Namespace
from getpass import getpass
from typing import Optional

from dstack.config import from_yaml_file, Profile, API_SERVER


def config(args: Namespace):
    conf = from_yaml_file(args.use_global_settings)
    if args.list:
        print("list of available profiles:\n")
        profiles = conf.list_profiles()
        for name in profiles:
            profile = profiles[name]
            print(name)
            print(f"\tUser: {profile.user}")
            print(f"\tToken: {show_token(profile.token)}")
            print(f"\tServer: {profile.server}")
        return

    if args.profile is not None:
        profile = conf.get_profile(args.profile)
        user = get_or_ask(args, profile, "user", "User: ", secure=False)
        token = get_or_ask(args, profile, "token", "Token: ", secure=True)
        if profile is None:
            profile = Profile(args.profile, user, token, args.server)
        elif args.force or (token != profile.token and confirm(
                f"Do you want to replace token for profile '{args.profile}'")):
            profile.token = token
        profile.server = args.server
        profile.user = user
        conf.add_or_replace_profile(profile)

    if args.remove is not None:
        if args.force or confirm(f"Do you want to delete profile '{args.remove}'"):
            conf.remove_profile(args.remove)

    conf.save()


def show_token(token: str):
    n = len(token)
    return f"{'*' * (n - 4)}{token[-4:]}"


def confirm(message: str) -> bool:
    reply = None
    while reply != "y" and reply != "n":
        reply = input(f"{message} (y/n)? ").lower().rstrip()
    return reply == "y"


def get_or_ask(args: Namespace, profile: Optional[Profile], field: str, prompt: str, secure: bool) -> str:
    old_value = getattr(profile, field) if profile is not None else None
    obj = getattr(args, field)
    if obj is None:
        value = None
        while value is None:
            value = getpass(prompt) if secure else input(prompt)
            value = value if value.strip() != "" else old_value
        return value
    else:
        return obj


def main():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    config_parser = subparsers.add_parser("config", help="manage your configuration")
    config_parser.add_argument("--token",
                               help="set token for selected profile",
                               type=str,
                               nargs="?")
    config_parser.add_argument("--server",
                               help="set server to handle api requests",
                               type=str,
                               nargs="?",
                               const=API_SERVER)
    config_parser.add_argument("--user",
                               help="set user name",
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
                              const="default",
                              type=str,
                              nargs="?")
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
