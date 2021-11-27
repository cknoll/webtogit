"""
Command line interface for autobrowser package
"""

import argparse
from ipydex import IPS, activate_ips_on_exception
from . import core

activate_ips_on_exception()


def main():

    cmd_mapping = {
        "cmd1": "cmd1 description",
        "cmd2": "cmd2 description",
        "cmd3": "cmd3 description",
    }

    cmd_docs = ", ".join([f"`{key}` ({value})" for key, value in cmd_mapping.items()])
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cmd", help=f"main command: allowed values: {cmd_docs}", choices=cmd_mapping.keys(), metavar="cmd"
    )

    args = parser.parse_args()

    if args.cmd:
        if args.cmd == "cmd1":
            core.script_main()
        elif args.cmd == "cmd2":
            core.script_main()
        elif args.cmd == "cmd3":
            core.script_main()
        else:
            print("unknown command")
    else:
        print("nothing to do, see option `--help` for more info")
