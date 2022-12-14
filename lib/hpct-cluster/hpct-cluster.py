#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpct-cluster.py

# enforce python3.8 or higher
import os
import sys


if sys.version_info.minor < 8:
    sys.argv.insert(0, "python3.8")
    try:
        os.execvp(sys.argv[0], sys.argv)
    except:
        print("error: requires python 3.8 or higher", file=sys.stderr)
        sys.exit(1)


import os
import os.path
import shutil
import signal
import subprocess
import sys
import yaml

sys.path.insert(0, "../vendor/hpct-managers/lib")

from hpctcluster.bundle import BUNDLE_APPNAMES, generate_bundle
from hpctcluster.juju import Juju
from hpctcluster.lib import run, run_capture
from hpctcluster.managers.snapd import SnapdManager

if os.path.exists("/etc/redhat-release"):
    from hpctmanagers.redhat import RedHatManager as DistroManager
else:
    from hpctmanagers.ubuntu import UbuntuManager as DistroManager


JUJU_EXEC = "/snap/bin/juju"
# TODO: remove hack
os.environ["PATH"] = f"""/var/lib/snapd/snap/bin:{os.environ["PATH"]}"""

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
        self.profile_path = os.path.abspath(f"{top_dir}/work/{profile_name}/main.yaml")

        try:
            # dirs
            self.work_dir = f"{top_dir}/work"
            self.work_profile_dir = f"{self.work_dir}/{profile_name}"

            # profiles
            self.profile = yaml.safe_load(open(self.profile_path).read())
            self.juju_profile = self.profile["juju"]
            self.lxd_profile = self.profile["lxd"]

            # charms
            self.charms_dir = f"{self.work_profile_dir}/charms"
            self.build_config_path = f"{self.work_profile_dir}/charms-builder/charms-builder.yaml"
            self.bundle_path = f"{self.work_profile_dir}/bundle.yaml"
            self.charms_builder_exec = f"{vendordir}/hpct-charms-builder/bin/charms-builder"

            # interview
            self.interview_config_path = f"{self.work_profile_dir}/interview/interview.yaml"
            self.interview_out_path = f"{self.work_profile_dir}/interview-out.yaml"
            self.interview_results = {}

            # juju
            self.juju = Juju(
                self.juju_profile["cloud"],
                self.juju_profile["controller"],
                self.juju_profile["model"],
            )
            self.juju_user = self.juju_profile["user"]
        except Exception as e:
            print(f"error: profile not complete ({e})", file=sys.stderr)
            sys.exit(1)

        # other
        self.username = os.environ["LOGNAME"]

        # managers
        self.charmcraft_manager = DistroManager(
            install_snaps=[
                {"name": "charmcraft", "args": ["--classic"]},
            ]
        )
        self.charmcraft_manager.set_verbose(True)

        self.juju_manager = DistroManager(
            install_snaps=[
                {"name": "juju", "args": ["--classic"]},
            ]
        )
        self.juju_manager.set_verbose(True)

        self.lxd_manager = DistroManager(
            install_snaps=[
                {"name": "lxd", "channel": "latest"},
            ]
        )
        self.lxd_manager.set_verbose(True)

        self.other_manager = DistroManager(
            install_packages=["terminator"],
        )
        self.other_manager.set_verbose(True)

        self.snapd_manager = SnapdManager()
        self.snapd_manager.set_verbose(True)

    def _info_general(self):
        print("GENERAL:")
        print(f"profile: {self.profile_name}")
        print(f"user: {self.username}")
        print(f"top dir: {top_dir}")
        print(f"etc dir: {etc_dir}")
        print(f"charms dir: {self.charms_dir}")
        print(f"work dir: {self.work_dir}")
        print(f"work profile dir: {self.work_profile_dir}")

        print()
        self._info_profiles()

        print()
        print("SNAPD:")
        print(f"snapd installed: {self.snapd_manager.is_installed()}")

        print()
        print("CHARMCRAFT:")
        print(f"charmcraft installed: {self.charmcraft_manager.is_installed()}")

        print()
        print("LXD:")
        print(f"lxd installed: {self.lxd_manager.is_installed()}")
        print(f"""lxd user: {self.lxd_profile["user"]}""")
        print(f"user in lxd group: {self.is_user_in_lxd_group()}")

        print()
        print("OTHER PACKAGES:")
        print(f"""native packages: {" ".join(self.other_manager.install_packages)}""")
        print(f"""snap packages: {" ".join(self.other_manager.install_snaps)}""")
        print(f"packages installed: {self.other_manager.is_installed()}")

        print()
        print("INTERVIEW:")
        print(f"""interview installed: {os.path.exists(self.interview_config_path)}""")

        print()
        print("BUNDLE:")
        print(f"""bundle path: {self.bundle_path}""")
        print(f"""bundle installed: {os.path.exists(self.bundle_path)}""")

        print()
        print("CHARMS:")
        cp = run_capture(
            [
                self.charms_builder_exec,
                "list-built",
                "-c",
                self.build_config_path,
                "-C",
                self.charms_dir,
            ],
            text=True,
        )
        built_charms = list(filter(None, cp.stdout.split("\n"))) if cp.returncode == 0 else []

        cp = run_capture(
            [
                self.charms_builder_exec,
                "list-missing",
                "-c",
                self.build_config_path,
                "-C",
                self.charms_dir,
            ],
            text=True,
        )
        missing_charms = list(filter(None, cp.stdout.split("\n"))) if cp.returncode == 0 else []

        all_charms = sorted(built_charms + missing_charms)
        for charm in all_charms:
            print(f"""{charm}: {"ready" if charm in built_charms else "missing"}""")

    def _info_juju(self):
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

    def _info_profiles(self):
        print("PROFILES:")
        src_profile_names = os.listdir(f"{etc_dir}/profiles")
        work_profile_names = os.listdir(self.work_dir)
        print(f"""source: {" ".join(sorted(src_profile_names))}""")
        print(f"""working: {" ".join(sorted(work_profile_names))}""")

    def _resolve_path(self, path, basedir):
        """Resolve non-"/"-prefixed path."""
        if path.startswith("/"):
            return path
        else:
            return f"{basedir}/{path}"

    def _setup_charmcraft(self):
        try:
            print("setting up charmcraft ...")
            self.charmcraft_manager.install()
            if not self.charmcraft_manager.is_installed():
                print("error: charmcraft setup failed", file=sys.stderr)
                return 1
            print("charmcraft setup complete")
        except:
            raise

    def _setup_cloud(self):
        if os.path.exists("/etc/oracle-cloud-agent"):
            self._setup_oracle_cloud()

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
                print("error: juju setup failed", file=sys.stderr)
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
                print("error: juju user setup failed", file=sys.stderr)
                return 1

            print("juju user setup complete")
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

            run(["usermod", "-a", "-G", "lxd", self.lxd_profile["user"]], decorate=True)

            if not self.lxd_manager.is_installed():
                print("error: lxd setup failed", file=sys.stderr)
                return 1

            print("lxd setup complete")
        except:
            raise

    def _setup_oracle_cloud(self):
        try:
            print("setting up for oracle cloud ...")

            # add lxd firewall ruleset
            run(["lxc", "network", "set", "lxdbr0", "ipv4.firewall", "true"], decorate=True)

            if os.path.exists("/etc/redhat-release"):
                # modify nftables ruleset
                run(["nft", "delete", "table", "inet", "firewalld"])

            else:
                # modify nftables ruleset
                run(["nft", "delete", "rule", "filter", "INPUT", "handle", "10"])
                run(["nft", "delete", "rule", "filter", "FORWARD", "handle", "11"])

            print("oracle cloud setup complete")
        except:
            raise

    def _setup_other(self):
        try:
            print("setting up other packages ...")
            self.other_manager.install()
            if not self.other_manager.is_installed():
                print("error: other packages setup failed", file=sys.stderr)
                return -1
            print("other packages setup complete")
        except:
            raise

    def _setup_snapd(self):
        try:
            print("setting up snapd ...")
            self.snapd_manager.install()

            if not self.snapd_manager.is_installed():
                print("error: snapd setup failed", file=sys.stderr)
                return -1

            if not self.snapd_manager.is_running():
                self.snapd_manager.enable()
                self.snapd_manager.start()
                if not self.snapd_manager.is_running():
                    print("error: snapd failed to start", file=sys.stderr)
                    return -1
            print("snapd setup complete")
        except:
            raise

    def build(self, series=None, charms=None):
        if charms == None:
            cp = run_capture([self.charms_builder_exec, "list", "-c", self.build_config_path])
            if cp.returncode != 0:
                raise Exception("cannot get charms list")
            charms = cp.stdout.split()
        # charms = ["hpct-head-node-operator"]

        cmdargs = [
            self.charms_builder_exec,
            "build",
            "-c",
            self.build_config_path,
            "-w",
            self.work_profile_dir,
            "-C",
            f"{self.charms_dir}",
        ]
        if series:
            cmdargs.extend(["-s", series])
        cmdargs.extend(charms)

        run(cmdargs, text=True, decorate=True)

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
        d["charm_home"] = self.charms_dir
        d["run-on"] = self.profile["charm"]["run-on"]
        generate_bundle(self.interview_results, self.bundle_path)

    def info(self):
        self._info_general()

        if self.username != "root":
            if self.juju_manager.is_installed():
                self.login()

        print()
        self._info_juju()

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

        # ensure that CTRL-C gets handled by the subprocess with this one being killed
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cp = run(args, text=True, decorate=True)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

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
            "charm_home": self.charms_dir,
            "nodes": {
                "ncompute": 1,
                "nhead": 1,
                "ninteractive": 0,
                "nldap": 1,
                "nslurm": 1,
            },
        }

        # update from interview
        if os.path.exists(self.interview_out_path):
            d = yaml.safe_load(open(self.interview_out_path).read())
            self.interview_results.update(d)

    def login(self):
        d = self.juju.whoami()
        juju_user = d.get("user", "")
        # print(f"""logging in as user ({juju_user})""")
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
                print("error: cannot find terminal", file=sys.stderr)
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
        self.info()
        self.interview()
        self.generate()
        self.build()

    def setup(self):
        if (
            self._setup_other() == 1
            or self._setup_snapd() == 1
            or self._setup_lxd() == 1
            or self._setup_cloud() == 1
            or self._setup_juju() == 1
            or self._setup_juju_user() == 1
            or self._setup_charmcraft() == 1
        ):
            print("*** setup failed ***")
            return 1

        print("*** setup completed successfully ***")

    def show_interview_results(self):
        if not os.path.exists(self.interview_out_path):
            print(f"error: failed to find interview results", file=sys.stderr)
            return 1

        print(open(self.interview_out_path).read())


def require_root():
    if os.getuid() != 0:
        print("error: run as root in another window", file=sys.stderr)
        sys.exit(1)


def main_build(control, args):
    try:
        charms = None
        series = None

        while args:
            arg = args.pop(0)
            if arg == "-s":
                series = args.pop(0)
            else:
                charms = [arg] + args
                del args[:]

        control.build(series, charms)
    except:
        print("error: build failed", file=sys.stderr)
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
    print("generate completed")


def main_info(control, args):
    try:
        # control.login()
        control.info()
    except:
        print("error: ensure juju is installed", file=sys.stderr)
        return 1


def main_init(control, args):
    """Initialize work directory and profile."""

    print("init running ...")
    try:
        src_profile_name = args.pop(0)
        if args:
            dst_profile_name = args.pop(0)
        else:
            dst_profile_name = src_profile_name
    except:
        print("error: missing profile name", file=sys.stderr)
        sys.exit(1)

    if os.getuid() == 0:
        print("error: run as non-root only", file=sys.stderr)
        sys.exit(1)

    try:
        src_profile_dir = f"{etc_dir}/profiles/{src_profile_name}"
        dst_profile_dir = f"{top_dir}/work/{dst_profile_name}"

        if not os.path.exists(src_profile_dir):
            print("error: failed to find profile directory", file=sys.stderr)
            sys.exit(1)

        if os.path.exists(dst_profile_dir):
            print("error: cannot overwrite working profile directory", file=sys.stderr)
            sys.exit(1)
        shutil.copytree(src_profile_dir, dst_profile_dir)

        # patch in lxd user name
        profile_path = f"{dst_profile_dir}/main.yaml"
        y = yaml.safe_load(open(profile_path, "r").read())
        y["lxd"]["user"] = os.environ["LOGNAME"]
        yaml.dump(y, open(profile_path, "w"))
    except SystemExit:
        raise
    except:
        print(f"error: failed to creating working profile ({dst_profile}")
        sys.exit(1)

    print(f"""update your environment with:\n\texport HPCT_PROFILE="{dst_profile_name}" """)
    print()
    print("init completed")


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
        print("error: setup failed", file=sys.stderr)
        return 1


def main_setup_charmcraft(control, args):
    control._setup_charmcraft()


def main_setup_juju(control, args):
    control._setup_juju()


def main_setup_lxd(control, args):
    control._setup_lxd()


def main_setup_other(control, args):
    control._setup_other()


def main_setup_juju_user(control, args):
    control._setup_juju_user()


def main_show_interview_results(control, args):
    control.show_interview_results()


def print_usage():
    PROGNAME = os.path.basename(sys.argv[0])
    print(
        f"""\
usage: {PROGNAME} init <profile>
       {PROGNAME} [-p <profile>] <cmd> [<opts> ...] [<arg> ...]
       {PROGNAME} -h|--help

Setup cluster. Each command supports its own options.

Typical steps are:
* init
* (as root) setup
* prepare
* monitor
* deploy

Commands:
build       Build charms.
cleanup     Remove bundled applications.
deploy      Deploy bundle.
info        Report status and other information.
init        Initialize working area and profile.
interview   Run interview and generate bundle.
monitor     Run status monitor in terminal window.
prepare     Run steps: interview, info, build

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

    name = f"hpct-cluster v{version}\n({commit})"
    uline = "=" * 48
    print(
        f"""\
{uline}
{name}
{uline}
"""
    )


if __name__ == "__main__":
    bindir = os.path.dirname(sys.argv[0])
    top_dir = os.path.abspath(f"{bindir}/..")
    etc_dir = os.path.abspath(f"{top_dir}/etc/hpct-cluster")
    vendordir = os.path.abspath(f"{top_dir}/vendor")

    profile_name = os.environ.get("HPCT_PROFILE")

    try:
        args = sys.argv[1:]
        cmd = args.pop(0)

        while args:
            arg = args.pop(0)
            if arg in ["-h", "--help"]:
                print_usage()
                sys.exit(0)
            elif arg == "-p":
                profile_name = args.pop(0)
            else:
                args.insert(0, arg)
                break

        if cmd in ["init"]:
            control = None
        elif profile_name == None:
            print("error: missing profile", file=sys.stderr)
            sys.exit(1)
        else:
            control = Control(profile_name)
            control.load_interview_results()
    except SystemExit:
        raise
    except:
        print("error: bad/missing arguments", file=sys.stderr)
        sys.exit(1)

    try:
        print_header()

        if cmd == "build":
            main_build(control, args)
        elif cmd == "cleanup":
            main_cleanup(control, args)
        elif cmd == "deploy":
            main_deploy(control, args)
        elif cmd == "info":
            main_info(control, args)
        elif cmd == "init":
            main_init(control, args)
        elif cmd == "interview":
            main_interview(control, args)
        elif cmd == "monitor":
            main_monitor(control, args)
        elif cmd == "prepare":
            main_prepare(control, args)
        elif cmd == "setup":
            main_setup(control, args)

        # unadvertised
        elif cmd == "generate":
            main_generate(control, args)
        elif cmd == "setup-charmcraft":
            main_setup_charmcraft(control, args)
        elif cmd == "setup-juju":
            main_setup_juju(control, args)
        elif cmd == "setup-juju-user":
            main_setup_juju_user(control, args)
        elif cmd == "setup-lxd":
            main_setup_lxd(control, args)
        elif cmd == "setup-other":
            main_setup_other(control, args)
        elif cmd == "show-interview-results":
            main_show_interview_results(control, args)
    except:
        raise
