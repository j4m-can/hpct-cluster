#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/juju.py

"""Temporary front-end to juju.

Future: Transition to python-libjuju.
"""

import json
import os
import os.path
import subprocess
import traceback

from hpctcluster.lib import run, run_capture


JUJU_EXEC = "/snap/bin/juju"


class Juju:
    def __init__(self, cloud, controller, model="admin/default"):
        self.cloud = cloud
        self.controller = controller
        self.model = model

    def add_model(self, model=None, *args):
        model = model or self.model
        cp = run([JUJU_EXEC, "add-model", model], text=True)
        return cp.returncode

    def add_user(self, username):
        cp = run([JUJU_EXEC, "add-user", username], text=True)
        return cp.returncode

    def bootstrap(self):
        print(
            f"bootstrapping juju controller cloud ({self.cloud}) controller ({self.controller}) ..."
        )
        d = self.controllers()
        controllers = d.get("controllers") or {}
        if controllers.get(self.controller):
            print("controller exists")
            return 0

        cp = run([JUJU_EXEC, "bootstrap", self.cloud, self.controller], text=True)
        if cp.returncode:
            print("juju bootstrap failed")
            raise Exception()

    def check_user(self, username):
        cp = run_capture([JUJU_EXEC, "show-user", username], text=True)
        return cp.returncode

    def controllers(self):
        cp = run_capture([JUJU_EXEC, "controllers", "--format", "json"], text=True)
        if cp.returncode != 0:
            return {}
        d = json.loads(cp.stdout)
        return d

    def deploy(self, charmpath, *args):
        model = self.model if "/" in self.model else f"admin/{self.model}"
        cp = run([JUJU_EXEC, "deploy", charmpath, "-m", model, *args], text=True)
        return cp.returncode

    def grant(self, username, rights, model):
        cp = run_capture([JUJU_EXEC, "grant", username, rights, model], text=True)
        return cp.returncode

    def is_controller_ready(self):
        cp = run_capture([JUJU_EXEC, "controllers", "--format", "json"], text=True)
        if cp.returncode == 0:
            d = json.loads(cp.stdout)
            if d.get("controllers", {}).get(self.controller):
                return True
        return False

    def is_model_ready(self):
        # TODO: why is the short model name not good enough?
        model = self.model if "/" in self.model else f"admin/{self.model}"

        cp = run_capture([JUJU_EXEC, "status", "-m", model], text=True)
        return True if not cp.returncode else False

    def is_ready(self):
        try:
            if not os.path.exists(JUJU_EXEC):
                return False

            cp = run_capture([JUJU_EXEC, "status"], text=True, timeout=5)
            return True if not cp.returncode else False
        except:
            traceback.print_exc()
            print("***")
            return False

    def is_user_ready(self, username):
        cp = run_capture([JUJU_EXEC, "users", "--format", "json"], text=True)
        if cp.returncode == 0:
            l = json.loads(cp.stdout)
            for d in l:
                if d.get("user-name") == username:
                    return True
        return False

    def login_user(self, username):
        cp = run([JUJU_EXEC, "login", "-u", username], text=True)
        return cp.returncode

    def logout_user(self):
        cp = run([JUJU_EXEC, "logout"], text=True)
        return cp.returncode

    def remove_application(self, appname, force=False):
        sargs = [JUJU_EXEC, "remove_application", appname, "--wait"]
        if force:
            sargs.append("--force")
        cp = run_capture(sargs, text=True)
        return cp.returncode

    def remove_applications(self, appnames, force=False):
        for appname in appnames:
            rv = self.remove_application(appname, force)

    def setup(self):
        """Set up juju, itself."""

        print("checking for controller ...")
        if not self.is_ready():
            self.bootstrap()

        print("checking model ...")
        if not self.is_model_ready():
            rv = self.add_model(self.model)
            if rv == 0:
                print(f"model ({self.model}) added")
            else:
                print(f"model ({self.model}) not added")
                return 1

    def xsetup(self):
        """Set up juju, itself.

        snap install lxd
        snap install juju
        """

        print("checking for lxd ...")
        if not self._is_lxd_installed():
            print("installing lxd ...")
            cp = run(["snap", "install", "lxd"], text=True)
            if cp.returncode:
                print("lxd installation failed")
                raise Exception()
        print("lxd installed/found")

        print("checking for juju ...")
        if not self._is_juju_installed():
            print("installing juju ...")
            cp = run(["snap", "install", "juju", "--classic"], text=True)
            if cp.returncode:
                print("juju installation failed")
                raise Exception()
        print("juju installed/found")

        print("checking for controller ...")
        if not self.is_ready():
            self.bootstrap()

        print("checking model ...")
        if not self.is_model_ready():
            rv = self.add_model(self.model)
            if rv == 0:
                print(f"model ({self.model}) added")
            else:
                print(f"model ({self.model}) not added")
                return 1

    def whoami(self):
        cp = run_capture([JUJU_EXEC, "whoami", "--format", "json"], text=True)
        if cp.returncode != 0 or cp.stderr != "":
            return {}
        return json.loads(cp.stdout)
