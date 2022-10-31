# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/managers/snapd.py

import os.path

from hpctmanagers import ManagerException, get_series
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


__series = get_series()
if __series.full in ["centos-8", "centos-9", "oracle-8", "oracle-9"]:
    SnapdManager = RedHatSnapdManager
elif __series.full in ["ubuntu-20.04", "ubuntu-22.04"]:
    SnapdManager = UbuntuSnapdManager
else:
    raise ManagerException("unsupported series")
