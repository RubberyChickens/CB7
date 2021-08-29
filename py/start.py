"""start.py - rwr-community-dev utility script for package testing.

Usage:
    start.py
"""
import enum
import queue
import dataclasses
import itertools
import sys
import time
import pathlib
import subprocess
import xml.etree.ElementTree as XmlET

from typing import Callable

# import docopt

# this magic allows for Ctrl+C to PyCharm run console to be handled nicely
try:
    from console_thrift import KeyboardInterruptException as KeyboardInterrupt  # noqa
except ImportError:
    pass

PY_DIR = pathlib.Path(__file__).parent
PKG_DIR, SCRIPTS_DIR = PY_DIR.parent, PY_DIR.parent / "scripts"
PKG_CFG = PKG_DIR / "package_config.xml"
RWR_ROOT = PKG_DIR.parent.parent.parent
RWR_GAME, RWR_SERV = RWR_ROOT / "rwr_game.exe", RWR_ROOT / "rwr_server.exe"
RWR_STEAM_URI = "steam://rungameid/270150//"


@dataclasses.dataclass
class PackageConfig:
    name: str
    description: str
    campaign_entry_script: str
    quickmatch_entry_script: str

    @classmethod
    def from_xml_file(cls, path: pathlib.Path):
        with path.open(mode="r", encoding="utf-8") as f:
            pkg_cfg_xml = XmlET.fromstring(f.read())
        name = pkg_cfg_xml.attrib["name"]
        description = pkg_cfg_xml.attrib["description"]
        campaign_entry_script = pkg_cfg_xml.attrib["campaign_entry_script"]
        quickmatch_entry_script = pkg_cfg_xml.attrib["quick_match_entry_script"]
        return cls(name, description, campaign_entry_script, quickmatch_entry_script)


def _consume_prompt(proc):
    # consume the prompt marker
    prompt_marker = proc.stdout.read(1)
    if prompt_marker != ">":
        # print(f"bad error = {proc.stdout.readline()}")
        raise Exception(f"prompt marker read got unexpected '{prompt_marker}' :/")


def wait_for_server_load(proc):
    _spinner_steps = itertools.cycle(["/", "-", "\\", "|"])
    while True:
        # read a line from rwr server stdout
        output_line = proc.stdout.readline()
        # strip the line for easier processing
        stripped_line = output_line.strip()
        # print(f"{stripped_line=!r}")
        if stripped_line.startswith("Loading"):
            _s = next(_spinner_steps)
            print(f"{_s} Loading...", end="\r")
        elif stripped_line == "Game loaded":
            # exit the while loop now
            break
        else:
            print(stripped_line)
    # consume the prompt marker
    # _consume_prompt(proc)
    return True


if __name__ == '__main__':
    path_to_package = f"media/packages/{PKG_DIR.name}"
    # args = docopt.docopt(__doc__)
    # print(f"docopt args={args}")

    print(f"Starting RWR from within '{PKG_DIR}'...")
    if not PKG_CFG.exists():
        print(f"Error: no package_config.xml found in '{PKG_DIR}' :/")
        sys.exit(1)

    print("Reading package config...")
    # with PKG_CFG.open(mode="r", encoding="utf-8") as f:
    pkg_cfg = PackageConfig.from_xml_file(PKG_CFG)
    print(f"Package name: {pkg_cfg.name}, script: {pkg_cfg.campaign_entry_script}")

    print("Locating RWR server executable...")
    if not RWR_SERV.exists():
        print(f"Error: couldn't find rwr_server in '{RWR_ROOT}' :cry:")
        sys.exit(2)

    print(f"Starting '{RWR_SERV}'...")
    rwr_serv_args = [f"{RWR_SERV}"]

    rwr_serv = subprocess.Popen(rwr_serv_args, cwd=RWR_ROOT.absolute(), encoding="utf-8",
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    try:
        # wait for the first prompt
        wait_for_server_load(rwr_serv)
        _consume_prompt(rwr_serv)
        print(f"Game loaded - sending start script for '{pkg_cfg.campaign_entry_script}'...")
        # write the start script command to rwr server stdin
        rwr_serv.stdin.write(f"start_script {pkg_cfg.campaign_entry_script} {path_to_package}\n")
        rwr_serv.stdin.flush()
        # consume the next prompt
        # _consume_prompt(rwr_serv)
        # wait again as the server now loads from overlays set in the script
        wait_for_server_load(rwr_serv)
        print(f"Package script loaded - starting server?!")
        # write the start server command to rwr server stdin

    except KeyboardInterrupt:
        print("Ctrl-C detected, shutting down!")
        rwr_serv.kill()

    #
    # ctx = Context.INIT
    # script_started = False
    # try:
    #     while True:
    #         if ctx == Context.INIT:
    #             # get lines, render nice, wait for `Game loaded` before proceeding
    #             output_line = rwr_serv.stdout.readline()
    #             stripped_line = output_line.strip()
    #             if stripped_line.startswith("Loading"):
    #                 print(f"{_s} Loading...", end="\r")
    #                 _s = next(_spinner_steps)
    #             elif stripped_line == "Game loaded":
    #                 # print(f"Game loaded - starting script '{pkg_cfg.campaign_entry_script}'...")
    #                 # rwr_serv.stdin.write("help\n")
    #                 # rwr_serv.stdin.flush()
    #                 ctx = Context.START_SCRIPT
    #         elif ctx == Context.START_SCRIPT:
    #             if not script_started:
    #                 print(f"Game loaded - starting script '{pkg_cfg.campaign_entry_script}'...")
    #                 rwr_serv.stdin.write(f"start_script {pkg_cfg.campaign_entry_script} {path_to_package}\n")
    #                 rwr_serv.stdin.flush()
    #                 script_started = True
    #             # get lines, render nice, wait for `Game loaded` before proceeding
    #             output_line = rwr_serv.stdout.readline()
    #             stripped_line = output_line.strip()
    #             if stripped_line.startswith("Loading"):
    #                 print(f"{_s} Loading...", end="\r")
    #                 _s = next(_spinner_steps)
    #             elif stripped_line == "Game loaded":
    #                 # TODO: add step to START_SERVER here
    #                 ctx = Context.START_SERVER
    #         elif ctx == Context.START_SERVER:
    #             print("Starting server...")
    #             # TODO: do it!
    #             ctx = Context.PRINT_STATUS
    #         elif ctx == Context.PRINT_STATUS:
    #             print("Collecting status info from rwr server...")
    #             # TODO: collect some status
    #             ctx = Context.WAIT
    #         elif ctx == Context.WAIT:
    #             output_line = rwr_serv.stdout.readline()
    #             # stripped_line = output_line.strip()
    #             print(output_line, end="")
    #         else:
    #             raise Exception("invalid context :/")
    #         # else:
    #         #     print(output_line, end="")
    # except KeyboardInterrupt:
    #     print("Ctrl-C detected, shutting down!")
    #     rwr_serv.kill()
    #     # rwr_serv.stdin.write("quit\n")
    #     # rwr_serv.stdin.flush()
