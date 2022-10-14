#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/bundle.py

import logging
import os.path

logger = logging.getLogger(__name__)


_BUNDLE_TEMPLATE = """
name: hpct-cluster-bundle

description: |
  Set up cluster.

#variables:

series: jammy

#tags:

applications:
  compute-node:
    charm: %(charmhome)s/hpct-compute-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: %(compute-nodes-count)s
    constraints: cores=2 mem=8G

  head-node:
    charm: %(charmhome)s/hpct-head-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: %(head-nodes-count)s
    constraints: cores=2 mem=4G

  interactive-node:
    charm: %(charmhome)s/hpct-interactive-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: %(interactive-nodes-count)s
    constraints: cores=2 mem=4G

  ldap-node:
    charm: %(charmhome)s/hpct-ldap-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: %(ldap-nodes-count)s
    constraints: cores=2 mem=4G

  nfs-node:
    charm: %(charmhome)s/hpct-nfs-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: 1
    constraints: cores=2 mem=4G

  slurm-node:
    charm: %(charmhome)s/hpct-slurm-node-operator_ubuntu-22.04-amd64.charm
    series: jammy
    num_units: %(slurm-nodes-count)s
    constraints: cores=2 mem=4G

  #
  # subordinates
  #
  ldap-client:
    charm: %(charmhome)s/hpct-ldap-client-operator_ubuntu-22.04-amd64.charm
    series: jammy

  ldap-server:
    charm: %(charmhome)s/hpct-ldap-server-operator_ubuntu-22.04-amd64.charm
    series: jammy

  slurm-client-compute:
    charm: %(charmhome)s/hpct-slurm-client-operator_ubuntu-22.04-amd64.charm
    series: jammy

  slurm-client:
    charm: %(charmhome)s/hpct-slurm-client-operator_ubuntu-22.04-amd64.charm
    series: jammy

  slurm-server:
    charm: %(charmhome)s/hpct-slurm-server-operator_ubuntu-22.04-amd64.charm
    series: jammy

relations:
# compute-node
- - compute-node:ldap-client-ready
  - ldap-client:ldap-client-ready
- - compute-node:slurm-client-ready
  - slurm-client-compute:slurm-client-ready

# head-node
- - head-node:ldap-client-ready
  - ldap-client:ldap-client-ready
- - head-node:slurm-client-ready
  - slurm-client:slurm-client-ready

# interactive-node
- - interactive-node:ldap-client-ready
  - ldap-client:ldap-client-ready
- - interactive-node:slurm-client-ready
  - slurm-client:slurm-client-ready

# ldap-node
- - ldap-node:ldap-server-ready
  - ldap-server:ldap-server-ready
- - ldap-node:ldap-client-ready
  - ldap-client:ldap-client-ready

# nfs-node
- - nfs-node:ldap-client-ready
  - ldap-client:ldap-client-ready

# slurm-node
- - slurm-node:ldap-client-ready
  - ldap-client:ldap-client-ready
- - slurm-node:slurm-client-ready
  - slurm-client:slurm-client-ready

# slurm-client
- - slurm-client:slurm-controller
  - slurm-server:slurm-controller

# slurm-client-compute
- - slurm-client-compute:slurm-controller
  - slurm-server:slurm-controller
- - slurm-client-compute:slurm-compute
  - slurm-server:slurm-compute
"""

BUNDLE_APPNAMES = [
    "compute-node",
    "head-node",
    "interactive-node",
    "ldap-node",
    "nfs-node",
    "slurm-node",
    "ldap-client",
    "ldap-server",
    "slurm-client",
    "slurm-client-compute",
    "slurm-server",
]


def generate_bundle(config, filename):
    with open(filename, "wt") as f:
        f.write(_BUNDLE_TEMPLATE % config)

    print(_BUNDLE_TEMPLATE % config)
    print(config)
