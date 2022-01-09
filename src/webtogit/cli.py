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
        metavar="reponame",
    )
    parser.add_argument(
        "--configfile-path",
        help=f"Set the path to the configuration directory (containing settings.yml).",
    )
    parser.add_argument(
        "--datadir-path",
        help=f"Set the path to the data directory.",
    )

    args = parser.parse_args()

    # IPS()
    if args.bootstrap_config:
        core.bootstrap_config(configfile_path=args.configfile_path)
        exit()

    if args.bootstrap:
        core.bootstrap_app(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    if args.bootstrap_repo:
        raise NotImplementedError("Bootstrapping of a new repository, additionally to the default one")
        exit()

    if args.print_config:
        core.print_config(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    # this is executed if no argument is passed

    repo_path = c.repo_paths[0]
    c.handle_repo(repo_path)


if __name__ == "__main__":
    # this block is called by a command like `python -m package.cli ...`
    # but not by the entry_points defined in setup.py
    main()
