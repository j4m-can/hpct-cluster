#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/lib.py

import subprocess


def run(*args, **kwargs):
    print("-------------------- ↓ ↓ ↓ ↓ ↓ --------------------")
    cp = subprocess.run(*args, **kwargs)
    print("-------------------- ↑ ↑ ↑ ↑ ↑ --------------------")
    return cp


def run_capture(*args, **kwargs):
    cp = subprocess.run(*args, **kwargs, capture_output=True)
    return cp
