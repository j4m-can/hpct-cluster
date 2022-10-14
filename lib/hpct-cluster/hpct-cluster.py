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

        try:
            # profiles
            self.profile = yaml.safe_load(open(self.profile_path).read())
            self.charms_profile = self.profile["charms"]
            self.interview_profile = self.profile["interview"]
            self.juju_profile = self.profile["juju"]
            self.lxd_profile = self.profile["lxd"]

            # dirs
            self.configdir = self._resolve_path(self.profile["config_dir"], etc_dir)
            self.work_dir = self._resolve_path(self.profile["work_dir"], top_dir)

            # create dirs only by non-root user
            if os.getuid() != 0:
                if not os.path.exists(self.work_dir):
                    try:
                        os.makedirs(self.work_dir)
                    except:
                        pass

            # charms
            self.charms_dir = self._resolve_path(self.charms_profile["home"], top_dir)
            self.build_config_path = self._resolve_path(
                self.charms_profile["builder_path"], etc_dir
            )
            self.bundle_path = self._resolve_path(
                self.charms_profile["bundle_name"], self.work_dir
            )

            # interview
            self.interview_config_path = self._resolve_path(
                self.interview_profile["path"], etc_dir
            )
            self.interview_out_path = self._resolve_path("interview.json", self.work_dir)
            self.interview_results = {}

            # juju
            self.juju = Juju(
                self.juju_profile["cloud"],
                self.juju_profile["controller"],
                self.juju_profile["model"],
            )
            self.juju_user = self.juju_profile["user"]
        except Exception as e:
            print("error: profile not complete ({e})")
            sys.exit(1)

        # other
        self.username = os.environ["LOGNAME"]

        # managers
        self.charmcraft_manager = UbuntuManager(
            install_snaps=[
                {"name": "charmcraft", "args": ["--classic"]},
            ]
        )
        self.charmcraft_manager.set_verbose(True)

        self.juju_manager = UbuntuManager(
            install_snaps=[
                {"name": "juju", "args": ["--classic"]},
            ]
        )
        self.juju_manager.set_verbose(True)

        self.lxd_manager = UbuntuManager(
            install_snaps=[
                {"name": "lxd", "channel": "latest"},
            ]
        )
        self.lxd_manager.set_verbose(True)

        self.terminator_manager = UbuntuManager(
            install_packages=["terminator"],
        )
        self.terminator_manager.set_verbose(True)

    def _check_general(self):
        print("GENERAL:")
        print(f"user: {self.username}")
        print(f"top dir: {top_dir}")
        print(f"etc dir: {etc_dir}")
        print(f"charms dir: {self.charms_dir}")
        print(f"work dir: {self.work_dir}")

        print()
        print("LXD:")
        print(f"lxd installed: {self.lxd_manager.is_installed()}")
        print(f"""lxd user: {self.lxd_profile["user"]}""")
        print(f"user in lxd group: {self.is_user_in_lxd_group()}")

        print()
        print("INTERVIEW:")
        print(f"""interview installed: {os.path.exists(self.interview_config_path)}""")
        print(f"""bundle: {self.charms_profile["bundle_name"]}""")
        print(f"""bundle installed: {os.path.exists(self.bundle_path)}""")

        print()
        print("CHARMCRAFT:")
        print(f"charmcraft installed: {self.charmcraft_manager.is_installed()}")

        print()
        print("TERMINAL APPLICATION:")
        print(f"terminator installed: {self.terminator_manager.is_installed()}")

    def _check_juju(self):
        print(f"JUJU:")
        print(f"""user: {self.juju_profile["user"]}""")
        print(f"""cloud: {self.juju_profile["cloud"]}""")
        print(f"""controller: {self.juju_profile["controller"]}""")
        print(f"""model: {self.juju_profile["model"]}""")

        print(f"juju installed: {self.juju_manager.is_installed()}")
        if self.juju_manager.is_installed():
            print(f"bootstrapped: {self.juju.is_ready()}")
            if self.juju.is_ready():
                print(f"""user ready: {self.juju.is_user_ready(self.juju_profile["user"])}""")
                print(f"""controller ready: {self.juju.is_controller_ready()}""")
                print(f"""model ready: {self.juju.is_model_ready()}""")

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

        run(sargs, text=True, decorate=True)

    def check(self):
        self._check_general()

        if self.username != "root":
            if self.juju_manager.is_installed():
                print("***")
                self.login()

        print()
        self._check_juju()

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
            reply = input("Existing results found. Do you want to redo the interview (y/n)? ")
            if reply in ["n"]:
                self.load_interview_results()
                return

        args = [
            f"{vendordir}/hpct-interview/bin/hpct-interview",
            "-o",
            self.interview_out_path,
            self.interview_config_path,
        ]
        print(args)
        cp = run(args, text=True, decorate=True)
        self.load_interview_results()

    def is_user_in_lxd_group(self):
        cp = run_capture(["id", "-nG", self.lxd_profile["user"]], text=True)
        if cp.returncode == 0:
            names = cp.stdout.split()
            if "lxd" in names:
                return True
        return False

    def load_interview_results(self):
        # defaults
        control.interview_results = {
            "charmhome": self.charms_dir,
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
        try:
            print("launching monitor ...")

            terminal = os.environ.get("TERMINAL")
            terminals = [terminal] if terminal else []
            terminals.extend(TERMINALS)

            for terminal in terminals:
                if os.path.exists(terminal):
                    print(f"found terminal program ({terminal})")
                    break
            else:
                print("error: cannot find terminal")
                return 1

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
        except:
            raise

    def prepare(self):
        self.check()
        self.interview()
        self.generate()
        self.build()

    def _setup_charmcraft(self):
        try:
            print("setting up charmcraft ...")
            self.charmcraft_manager.install()
            if not self.charmcraft_manager.is_installed():
                print("error: charmcraft setup failed")
                return 1
            print("charmcraft setup complete")
        except:
            raise

    def _setup_juju(self):
        try:
            print("setting up juju ...")

            self.juju_manager.install()
            self.juju_manager.enable()
            self.juju_manager.start()

            print("checking for juju ...")
            if self.juju.is_ready():
                print("juju is running")
            else:
                print("running juju setup ...")
                self.juju.setup()

            if not self.juju_manager.is_running() or not self.juju.is_ready():
                print("error: juju setup failed")
                return 1

            print("juju setup complete")
        except:
            raise

    def _setup_juju_user(self):
        try:
            print(f"""setting up cluster admin user and rights in juju ...""")

            username = self.lxd_profile["user"]

            if self.juju.check_user(self.juju_user) == 0:
                print("user already set up")
            else:
                print(f"adding user ({self.juju_user})")
                self.juju.add_user(self.juju_user)

                print(
                    f"""\n\033[5m>>> User "{username}", run the "juju register" command above.\033[0m"""
                )
                _ = input("Press ENTER once the user has registered. ")
                print()

            print("granting rights ...")
            self.juju.grant(self.juju_user, "admin", self.juju_profile["model"])

            print(
                f"""The clusteradmin user should run "juju switch admin/{self.juju_profile["model"]}".\n"""
                f"""\n\033[5m>>> User "{username}", run the "juju switch" command above.\033[0m"""
            )
            _ = input("Press ENTER once the user has registered. ")
            print()

            if self.juju.check_user(self.juju_user) != 0:
                print("error: juju user setup failed")
                return 1

            print("juju user setup complete")
        except:
            raise

    def _setup_terminator(self):
        try:
            print("setting up terminator ...")
            self.terminator_manager.install()
            if not self.terminator_manager.is_installed():
                print("error: terminator setup failed")
                return -1
            print("terminator setup complete")
        except:
            raise

    def _setup_lxd(self):
        try:
            print("setting up lxd ...")

            self.lxd_manager.install()
            if not self.lxd_manager.is_enabled():
                self.lxd_manager.enable()
            if not self.lxd_manager.is_running():
                self.lxd_manager.start()

            run(["adduser", self.lxd_profile["user"], "lxd"], decorate=True)

            if not self.lxd_manager.is_installed():
                print("error: lxd setup failed")
                return 1

            print("lxd setup complete")
        except:
            raise

    def setup(self):
        self._setup_terminator()
        # TODO: add check

        if (
            self._setup_lxd() == 1
            or self._setup_juju() == 1
            or self._setup_juju_user() == 1
            or self._setup_charmcraft() == 1
        ):
            print("*** setup failed ***")
            return 1

        print("*** setup completed successfully ***")

    def show_interview_results(self):
        if not os.path.exists(self.interview_out_path):
            print(f"error: failed to find interview results")
            return 1

        d = json.loads(open(self.interview_out_path).read())
        print(json.dumps(d, indent=2))


def require_root():
    if os.getuid() != 0:
        print("error: run as root in another window")
        sys.exit(1)


def main_build(control, args):
    try:
        charms = args[:] if args else None
        control.build(charms)
    except:
        traceback.print_exc()
        print("error: build failed", file=sys.stderr)
        return 1


def main_check(control, args):
    try:
        # control.login()
        control.check()
    except:
        traceback.print_exc()
        print("error: ensure juju is installed", file=sys.stderr)
        return 1


def main_cleanup(control, args):
    try:
        control.cleanup()
    except:
        print("error: cleanup failed", file=sys.stderr)
        return 1


def main_deploy(control, args):
    try:
        control.login()
        control.deploy()
    except:
        print("error: deploy failed", file=sys.stderr)
        return 1


def main_generate(control, args):
    try:
        control.generate()
    except:
        print("error: generate failed", file=sys.stderr)
        return 1


def main_interview(control, args):
    try:
        control.interview()
        control.generate()
    except:
        print("error: interview failed", file=sys.stderr)
        return 1


def main_monitor(control, args):
    try:
        control.login()
        control.monitor()
    except:
        print("error: monitor failed", file=sys.stderr)
        return 1


def main_prepare(control, args):
    try:
        control.prepare()
    except:
        print("error: prepare failed", file=sys.stderr)
        return 1


def main_setup(control, args):
    try:
        control.setup()
    except:
        traceback.print_exc()
        print("error: setup failed", file=sys.stderr)
        return 1


def main_setup_charmcraft(control, args):
    control._setup_charmcraft()


def main_setup_juju(control, args):
    control._setup_juju()


def main_setup_lxd(control, args):
    control._setup_lxd()


def main_setup_terminator(control, args):
    control._setup_terminator()


def main_setup_juju_user(control, args):
    control._setup_juju_user()


def main_show_interview_results(control, args):
    control.show_interview_results()


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


def print_header():
    version = "0.1"
    try:
        commit = "-"
        cp = run_capture(["git", "rev-parse", "HEAD"], text=True)
        if cp.returncode == 0:
            commit = cp.stdout.strip()
    except:
        pass

    name = f"hpct-cluster (v{version}) ({commit})"
    uline = "-" * len(name)
    print(
        f"""\
{name}
{uline}
"""
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
        print_header()

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
            case "setup-charmcraft":
                main_setup_charmcraft(control, args)
            case "generate":
                main_generate(control, args)
            case "setup-juju":
                main_setup_juju(control, args)
            case "setup-juju-user":
                main_setup_juju_user(control, args)
            case "setup-lxd":
                main_setup_lxd(control, args)
            case "setup-terminator":
                main_setup_terminator(control, args)
            case "show-interview-results":
                main_show_interview_results(control, args)
    except:
        raise
