"""
Command line interface for padstogit package
"""

import argparse
from ipydex import IPS, activate_ips_on_exception, TracerFactory
from . import core

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
        "--config-path",
        help=f"Set the path to the configuration directory (containing settings.yml).",
    )
    parser.add_argument(
        "--data-path",
        help=f"Set the path to the data directory.",
    )

    args = parser.parse_args()

    c = core.Core(data_path=args.data_path, config_path=args.config_path)

    if args.bootstrap:
        core.bootstrap_app()
        exit()

    if args.print_config:
        c.print_config()
        exit()

    c.main()


if __name__ == "__main__":
    main()
