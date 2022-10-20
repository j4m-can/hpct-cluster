# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/managers/snapd.py

import os.path

from hpctmanagers.redhat import RedHatManager
from hpctmanagers.ubuntu import UbuntuManager


class RedHatSnapdManager(RedHatManager):
    install_packages = [
        "https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm",
        "snapd",
    ]
    systemd_services = [
        "snapd",
    ]

    def install(self):
        super().install()

        if not os.path.exists("/snap"):
            os.symlink("/var/lib/snapd/snap", "/snap")


class UbuntuSnapdManager(UbuntuManager):
    install_packages = [
        "snapd",
    ]
    systemd_services = [
        "snapd",
    ]


# TODO: not ideal but works
if os.path.exists("/etc/redhat-release"):
    SnapdManager = RedHatSnapdManager
else:
    SnapdManager = UbuntuSnapdManager
