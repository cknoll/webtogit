"""
Command line interface for webtogit package
"""

import argparse
import logging
from ipydex import IPS, activate_ips_on_exception, TracerFactory
from . import core, util as u

activate_ips_on_exception()
ST = TracerFactory()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--print-config",
        help=f"Print the current configuration (and all relevant paths). Then exit.",
        action="store_true",
    )
    parser.add_argument(
        "--bootstrap",
        help=f"Initialize the application (config and data-path). Warn if dirs/files exist.",
        action="store_true",
    )
    parser.add_argument(
        "--bootstrap-config",
        help=f"Initialize the configuration of the application.",
        action="store_true",
    )
    parser.add_argument(
        "--bootstrap-repo",
        help=f"Initialize a new (additional) repo.",
        metavar="REPONAME",
    )
    parser.add_argument(
        "--configfile-path",
        help=f"Set the path to the configuration directory (containing settings.yml).",
    )
    parser.add_argument(
        "--datadir-path",
        help=f"Set the path to the data directory.",
    )
    parser.add_argument(
        "reponame",
        help=(
            f"The repository which should be updated (based on its {core.APPNAME}-sources.yml)\n"
            f"default: {core.DEFAULT_REPO_NAME}"
        ),
        default=core.DEFAULT_REPO_NAME,
        nargs="?",
    )
    parser.add_argument(
        "--update-all-repos",
        help=f"Update all repositories",
        action="store_true",
    )

    args = parser.parse_args()

    if args.bootstrap_config:
        core.bootstrap_config(configfile_path=args.configfile_path)
        exit()

    elif args.bootstrap:
        core.bootstrap_app(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    elif args.bootstrap_repo:
        core.bootstrap_datadir(
            configfile_path=args.configfile_path,
            datadir_path=args.datadir_path,
            repo_name=args.bootstrap_repo,
        )
        exit()

    elif args.print_config:
        core.print_config(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    elif args.update_all_repos:
        core.update_all_repos(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    else:
        # this is executed if no argument is passed
        core.update_repo(args.reponame)
        exit()


if __name__ == "__main__":
    # this block is called by a command like `python -m package.cli ...`
    # but not by the entry_points defined in setup.py
    main()
