#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/bundle.py

import logging

from hpctcluster.lib import DottedDictWrapper

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
    charm: %(charm_home)s/hpct-compute-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: %(nodes.ncompute)s
    constraints: cores=2 mem=8G

  head-node:
    charm: %(charm_home)s/hpct-head-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: %(nodes.nhead)s
    constraints: cores=2 mem=4G

  interactive-node:
    charm: %(charm_home)s/hpct-interactive-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: %(nodes.ninteractive)s
    constraints: cores=2 mem=4G

  ldap-node:
    charm: %(charm_home)s/hpct-ldap-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: %(nodes.nldap)s
    constraints: cores=2 mem=4G

  nfs-node:
    charm: %(charm_home)s/hpct-nfs-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: 1
    constraints: cores=2 mem=4G

  slurm-node:
    charm: %(charm_home)s/hpct-slurm-node-operator_%(charm-run-on)s.charm
    #series: jammy
    num_units: %(nodes.nslurm)s
    constraints: cores=2 mem=4G

  #
  # subordinates
  #
  ldap-client:
    charm: %(charm_home)s/hpct-ldap-client-operator_%(charm-run-on)s.charm
    #series: jammy

  ldap-server:
    charm: %(charm_home)s/hpct-ldap-server-operator_%(charm-run-on)s.charm
    #series: jammy

  slurm-client-compute:
    charm: %(charm_home)s/hpct-slurm-client-operator_%(charm-run-on)s.charm
    #series: jammy

  slurm-client:
    charm: %(charm_home)s/hpct-slurm-client-operator_%(charm-run-on)s.charm
    #series: jammy

  slurm-server:
    charm: %(charm_home)s/hpct-slurm-server-operator_%(charm-run-on)s.charm
    #series: jammy

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
- - slurm-node:slurm-server-ready
  - slurm-server:slurm-server-ready

# ldap-client
- - ldap-server:ldap-info
  - ldap-client:ldap-info

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
    dd = DottedDictWrapper(config, ".")

    with open(filename, "wt") as f:
        f.write(_BUNDLE_TEMPLATE % dd)

    print(_BUNDLE_TEMPLATE % dd)
