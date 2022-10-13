#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpct-cluster.py

import json
import os
import os.path
import subprocess
import sys
import traceback
import yaml

from hpctcluster.bundle import BUNDLE_APPNAMES, generate_bundle
from hpctcluster.juju import Juju
from hpctcluster.lib import run, run_capture

sys.path.insert(0, "../vendor/hpct-managers/lib")
from hpctmanagers.ubuntu import UbuntuManager

JUJU_EXEC = "/snap/bin/juju"

CLOUD_NAME = "localhost"
CLUSTER_ADMIN = "cluster-admin"
CONTROLLER_NAME = "cluster"
MODEL_NAME = "admin/default"

TERMINALS = [
    "x-terminal-emulator",
    "/usr/bin/terminator",
    "/usr/bin/gnome-terminal",
    "konsole",
]


class Control:
    def __init__(self, profile_name):
        global top_dir, etc_dir

        self.profile_name = profile_name
        self.profile_path = os.path.abspath(
            f"{top_dir}/etc/hpct-cluster/profiles/{profile_name}.yaml"
        )

        self.profile = yaml.safe_load(open(self.profile_path).read())

        self.charms_dir = self._resolve_path(self.profile["charms_dir"], top_dir)
        self.configdir = self._resolve_path(self.profile["config_dir"], etc_dir)
        self.work_dir = self._resolve_path(self.profile["work_dir"], top_dir)

        if not os.path.exists(self.work_dir):
            try:
                os.makedirs(self.work_dir)
            except:
                pass

        self.build_config_path = f"{self.configdir}/charms-builder.yaml"

        self.interview_config_path = self._resolve_path(self.profile["interview_path"], etc_dir)
        self.interview_out_path = self._resolve_path("interview.json", self.work_dir)
        self.bundle_path = self._resolve_path(self.profile["bundle_name"], self.work_dir)

        self.interview_results = {}
        self.juju = Juju(self.profile["cloud"], self.profile["controller"], self.profile["model"])

        self.juju_user = self.profile["user"]
        self.username = os.environ["LOGNAME"]

        self.charmcraft_manager = UbuntuManager(
            install_snaps=[
                {"name": "charmcraft", "args": ["--classic"]},
            ]
        )
        self.juju_manager = UbuntuManager(
            install_snaps=[
                {"name": "juju", "args": ["--classic"]},
            ]
        )
        self.lxd_manager = UbuntuManager(
            install_snaps=[
                {"name": "lxd", "channel": "latest"},
            ]
        )
        self.terminator_manager = UbuntuManager(
            install_packages=["terminator"],
        )

    def _resolve_path(self, path, basedir):
        """Resolve non-"/"-prefixed path."""
        if path.startswith("/"):
            return path
        else:
            return f"{basedir}/{path}"

    def build(self, charms=None):
        build_charms_exec = f"{vendordir}/hpct-charms-builder/bin/build-charms"

        if charms == None:
            cp = run_capture([build_charms_exec, "-c", self.build_config_path, "-l"])
            if cp.returncode != 0:
                raise Exception("cannot get charms list")
            charms = cp.stdout.split()
        # charms = ["hpct-head-node-operator"]

        sargs = [
            build_charms_exec,
            "-c",
            self.build_config_path,
            "-w",
            self.work_dir,
            "-C",
            f"{self.charms_dir}",
        ] + charms

        cp = run(sargs)
        print(cp.returncode)

    def check(self):
        self.check_general()
        print()
        self.check_juju()

    def check_general(self):
        print("GENERAL:")
        print(f"user: {self.username}")
        print(f"lxd installed: {self.lxd_manager.is_installed()}")
        print(f"user in lxd group: {self.is_user_in_lxd_group()}")
        print(f"charmcraft installed: {self.charmcraft_manager.is_installed()}")
        print(f"terminator installed: {self.terminator_manager.is_installed()}")

    def check_juju(self):
        print(f"JUJU:")
        print(f"user: {self.juju_user}")
        print(f"installed: {self.juju_manager.is_installed()}")
        if self.juju_manager.is_installed():
            print(f"bootstrapped: {self.juju.is_ready()}")
            if self.juju.is_ready():
                print(f"""model ({self.profile["model"]}): {self.juju.is_model_ready()}""")
        print(f"""bundle ({self.profile["bundle_name"]}): {os.path.exists(self.bundle_path)}""")

    def cleanup(self):
        self.juju.remove_applications(BUNDLE_APPNAMES)

    def deploy(self):
        # deploy bundle
        self.juju.deploy(f"{self.bundle_path}")

    def generate(self):
        print("generating bundle ...")
        if os.path.exists(self.bundle_path):
            os.remove(self.bundle_path)
        d = self.interview_results.copy()
        d["charmhome"] = self.charms_dir
        generate_bundle(self.interview_results, self.bundle_path)

    def interview(self):
        # interview
        print("run interview ...")
        if os.path.exists(self.interview_out_path):
            reply = input("Do you want to redo the interview (y/n)? ")
            if reply in ["n"]:
                self.load_interview_results()
                return

        cp = run(
            [
                f"{vendordir}/hpct-interview/bin/hpct-interview",
                "-o",
                self.interview_out_path,
                self.interview_config_path,
            ]
        )
        self.load_interview_results()

    def is_charmcraft_installed(self):
        cp = run_capture(["snap", "list", "charmcraft"])
        return cp.returncode == 0 and True or False

    def is_lxd_installed(self):
        cp = run_capture(["snap", "list", "lxd"])
        return cp.returncode == 0 and True or False

    def is_terminator_installed(self):
        cp = run_capture(["dpkg", "-l", "terminator"])
        return cp.returncode == 0 and True or False

    def is_user_in_lxd_group(self):
        cp = run_capture(["id", "-nG", self.username], text=True)
        if cp.returncode == 0:
            names = cp.stdout.split()
            if "lxd" in names:
                return True
        return False

    def load_interview_results(self):
        # defaults
        control.interview_results = {
            "charmhome": "~/charms",
            "compute-nodes-count": 1,
            "head-nodes-count": 1,
            "interactive-nodes-count": 0,
            "ldap-nodes-count": 1,
            "slurm-nodes-count": 1,
        }

        # update from interview
        if os.path.exists(self.interview_out_path):
            d = json.loads(open(self.interview_out_path).read())
            self.interview_results.update(d)

    def login(self):
        d = self.juju.whoami()
        juju_user = d.get("user", "")
        print(f"""logging in as user ({juju_user})""")
        if juju_user != self.juju_user:
            self.juju.logout_user()
            self.juju.login_user(self.juju_user)

    def monitor(self):
        terminal = os.environ.get("TERMINAL")
        terminals = [terminal] if terminal else []
        terminals.extend(TERMINALS)

        for terminal in terminals:
            if os.path.exists(terminal):
                break
        else:
            print("error: cannot find terminal")
            sys.exit(1)

        try:
            if os.fork() == 0:
                subprocess.run(
                    [terminal, "-x", JUJU_EXEC, "status", "--relations", "--watch", "5s"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except:
            pass

    def prepare(self):
        self.check()
        self.interview()
        self.generate()
        self.build()

    def _setup_charmcraft(self):
        run(["snap", "install", "charmcraft", "--classic"])

    def _setup_lxd(self):
        run(["snap", "install", "lxd", "--channel=latest"])

    def _setup_juju(self):
        self.juju.setup()
        return

        print("checking for juju ...")
        if self.juju.is_ready():
            print("juju is running")
        else:
            print("running juju setup ...")
            self.juju.setup()

    def _setup_juju_user(self):
        print("setting up cluster admin user and rights in juju ...")
        if self.juju.check_user(self.juju_user) == 0:
            print("user already set up")
        else:
            print(f"adding user ({self.juju_user})")
            self.juju.add_user(self.juju_user)

            print("""\n\033[5m>>> In user console, run "juju register ...".\033[0m""")
            _ = input("Press ENTER once the user has registered. ")
            print()

        print("granting rights ...")
        self.juju.grant(self.juju_user, "admin", self.profile["model"])

        print(
            f"""\n\033[5m>>> In user console, run "juju switch admin/{self.profile["model"]}".\033[0m"""
        )
        _ = input("Press ENTER once the user has registered. ")
        print()

    def _setup_terminator(self):
        run(["apt", "install", "-y", "terminator"])

    def _setup_user_in_lxd_group(self):
        run(["adduser", self.username, "lxd"])

    def setup(self):
        self._setup_terminator()
        # TODO: add check

        self._setup_lxd()
        if not self.check_lxd():
            print("error: failed to set up lxd")
            return 1

        self._setup_juju()
        if not self.juju.is_ready():
            print("error: failed to set up juju")
            return 1

        self._setup_juju_user()
        if self.juju.check_user(self.juju_user) != 0:
            print("error: failed to set up user")
            return 1

        self._setup_user_in_lxd_group()
        if not self.check_user_group():
            print(f"error: user ({self.username}) not in lxd group")
            return 1

        self._setup_charmcraft()
        if not self.check_charmcraft():
            print(f"error: failed to set up charmcraft")
            return 1

        print("*** setup completed successfully ***")


def require_root():
    if os.getuid() != 0:
        print("error: run as root in another window")
        sys.exit(1)


def main_build(control, args):
    charms = args[:] if args else None
    control.build(charms)


def main_check(control, args):
    try:
        control.login()
        control.check()
    except:
        traceback.print_exc()
        print("error: ensure juju is installed")
        return 1


def main_cleanup(control, args):
    control.cleanup()


def main_deploy(control, args):
    control.login()
    control.deploy()


def main_interview(control, args):
    control.interview()
    control.generate()


def main_monitor(control, args):
    control.login()
    control.monitor()


def main_prepare(control, args):
    control.prepare()


def main_setup(control, args):
    control.setup()


def main_setup_juju(control, args):
    control._setup_juju()


def main_setup_user(control, args):
    control._setup_user()


def print_usage():
    PROGNAME = os.path.basename(sys.argv[0])
    print(
        f"""\
usage: {PROGNAME} [-p <profile>] <cmd> [<opts> ...] [<arg> ...]
       {PROGNAME} -h|--help

Setup cluster. Each command supports its own options.

Typical steps are:
* (as root) setup
* prepare
* deploy

Commands:
build       Build charms.
check       Check statuses of various items.
cleanup     Remove bundled applications.
deploy      Deploy bundle.
interview   Run interview and generate bundle.
monitor     Run status monitor in terminal window.
prepare     Run steps: interview, check, build

Root commands (run as root):
setup       Set up juju.

Commands marked with * must be run as root."""
    )


if __name__ == "__main__":
    bindir = os.path.dirname(sys.argv[0])
    top_dir = os.path.abspath(f"{bindir}/..")
    etc_dir = os.path.abspath(f"{top_dir}/etc/hpct-cluster")
    vendordir = os.path.abspath(f"{top_dir}/vendor")

    # TODO: move these into Control
    profile_name = "cluster"

    try:
        cmd = None

        args = sys.argv[1:]

        while args:
            arg = args.pop(0)
            if arg in ["-h", "--help"]:
                print_usage()
                sys.exit(0)
            elif arg == "-p":
                profile_name = args.pop(0)
            elif not arg.startswith("-"):
                cmd = arg
                break
            else:
                raise Exception()

        control = Control(profile_name)
        control.load_interview_results()
    except SystemExit:
        raise
    except:
        traceback.print_exc()
        print("error: bad/missing arguments")
        sys.exit(1)

    try:
        match cmd:
            case "build":
                main_build(control, args)
            case "check":
                main_check(control, args)
            case "cleanup":
                main_cleanup(control, args)
            case "deploy":
                main_deploy(control, args)
            case "interview":
                main_interview(control, args)
            case "monitor":
                main_monitor(control, args)
            case "prepare":
                main_prepare(control, args)
            case "setup":
                main_setup(control, args)

            # unadvertised
            case "setup-juju":
                main_setup_juju(control, args)
            case "setup-user":
                main_setup_user(control, args)
    except:
        raise
