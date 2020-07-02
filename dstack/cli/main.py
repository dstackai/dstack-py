import subprocess
import sys
from argparse import ArgumentParser, Namespace

from dstack.cli import confirm, get_or_ask
from dstack.cli.installer import Installer
from dstack.config import from_yaml_file, Profile, API_SERVER, _get_config_path
from dstack.logger import hide_token
from dstack.version import __version__ as version


def config(args: Namespace):
    conf = from_yaml_file(_get_config_path(args.use_global_settings))
    if args.list:
        print("list of available profiles:\n")
        profiles = conf.list_profiles()
        for name in profiles:
            profile = profiles[name]
            print(name)
            print(f"\tUser: {profile.user}")
            print(f"\tToken: {hide_token(profile.token)}")
            if profile.server != API_SERVER:
                print(f"\tServer: {profile.server}")

    if args.profile is not None:
        profile = conf.get_profile(args.profile)
        user = get_or_ask(args, profile, "user", "User: ", secure=False)
        token = get_or_ask(args, profile, "token", "Token: ", secure=True)
        if profile is None:
            profile = Profile(args.profile, user, token, args.server, not args.no_verify)
        elif args.force or (token != profile.token and confirm(
                f"Do you want to replace token for profile '{args.profile}'")):
            profile.token = token
        profile.server = args.server
        profile.user = user
        profile.verify = not args.no_verify
        conf.add_or_replace_profile(profile)

    if args.remove is not None:
        if args.force or confirm(f"Do you want to delete profile '{args.remove}'"):
            conf.remove_profile(args.remove)

    conf.save()


def server(args: Namespace):
    srv = Installer()

    if args.install or args.update:
        if srv.update():
            print("Server is successfully updated")
        else:
            print("Server is up to date")

    if args.version:
        print(srv.version() or "Server is not installed")

    if args.start:
        java = srv.find_jdk()

        if not java:
            print("Can't find java")
        else:
            try:
                subprocess.run([java.path(), "-jar", srv.jar_path()])
            except KeyboardInterrupt:
                print("Server stopped")


def main():
    parser = ArgumentParser(epilog="Please visit https://docs.dstack.ai for more information")
    parser.add_argument("--version", action="version", version=f"{version}")
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
                               default=API_SERVER,
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
    config_parser.add_argument("--no-verify",
                               help="do not verify SSL certificates",
                               dest="no_verify",
                               action="store_true")
    config_group = config_parser.add_mutually_exclusive_group()
    config_group.add_argument("--profile",
                              help="use profile or create a new one",
                              const="default",
                              type=str,
                              nargs="?",
                              default="default")
    config_group.add_argument("--remove",
                              help="remove existing profile",
                              type=str,
                              metavar="PROFILE")
    config_group.add_argument("--list",
                              help="list configured profiles",
                              action="store_true")
    config_parser.set_defaults(func=config)

    server_parser = subparsers.add_parser("server", help="manage your dstack server")
    server_group = server_parser.add_mutually_exclusive_group()
    server_group.add_argument("--install",
                              help="install server",
                              action="store_true")
    server_group.add_argument("--update",
                              help="update server",
                              action="store_true")
    server_group.add_argument("--start",
                              help="start server",
                              action="store_true")
    server_group.add_argument("--version",
                              help="print server version",
                              action="store_true")

    server_parser.set_defaults(func=server)

    if len(sys.argv) < 2:
        parser.print_help()
        exit(1)

    args = parser.parse_args()
    args.func(args)
