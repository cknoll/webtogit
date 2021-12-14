"""
Command line interface for padstogit package
"""

import argparse
from ipydex import IPS, activate_ips_on_exception, TracerFactory
from . import core, util as u

ST = TracerFactory()
activate_ips_on_exception()


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
        "--configfile-path",
        help=f"Set the path to the configuration directory (containing settings.yml).",
    )
    parser.add_argument(
        "--datadir-path",
        help=f"Set the path to the data directory.",
    )

    args = parser.parse_args()


    if args.bootstrap_config:
        core.bootstrap_config(configfile_path=args.configfile_path)
        exit()

    if args.bootstrap:
        core.bootstrap_app(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
        exit()

    try:
        c = core.Core(configfile_path=args.configfile_path, datadir_path=args.datadir_path)
    except FileNotFoundError as err:
        print(u.bred("Error:"), err)
        exit(1)


    if args.print_config:
        c.print_config()
        exit()

    c.handle_repo()


if __name__ == "__main__":
    main()
