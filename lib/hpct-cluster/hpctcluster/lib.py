#! /usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
#
# hpctcluster/lib.py

import subprocess


class DottedDictWrapper:
    """Wrap an existing dictionary to provide dotted notation
    for keys.

    See https://gist.github.com/j4m-can/d843ed08b0e29125cacb2d5ea349b46a.
    """

    def __init__(self, d=None, sep="."):
        self.d = d if d != None else {}
        self.sep = sep

    def _find(self, keys):
        v = self.d
        for k in keys:
            if isinstance(v, dict):
                v = v[k]
            else:
                raise KeyError()
        return v

    def _walk(self, d, pref=None):
        for k in d:
            _pref = f"{pref}{self.sep}{k}" if pref else k
            v = d[k]
            if isinstance(v, dict):
                yield from self._walk(v, _pref)
            else:
                yield (_pref, v)

    def __contains__(self, key):
        try:
            v = self._find(key.split(self.sep))
        except:
            return False
        return True

    def __getitem__(self, key):
        try:
            v = self._find(key.split(self.sep))
            if isinstance(v, dict):
                v = DottedDictWrapper(v, self.sep)
        except:
            raise
        return v

    def __setitem__(self, key, value):
        keys = key.split(self.sep)
        try:
            v = self.d
            for key in keys[:-1]:
                if key not in v:
                    v[key] = {}
                    v = v[key]
                elif isinstance(v, dict):
                    v = v[key]
                else:
                    # already set
                    raise Exception()
            v[keys[-1]] = value
        except:
            raise KeyError()

    def __str__(self):
        return str(self.d)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def keys(self):
        for k, _ in self._walk(self.d):
            yield k

    def items(self):
        for k, v in self._walk(self.d):
            yield (k, v)

    def update(self, d):
        self.d.update(d)

    def values(self):
        for _, v in self._walk(self.d):
            yield v


def run(*args, **kwargs):
    try:
        if decorate := kwargs.pop("decorate", False):
            print("-------------------- ↓ ↓ ↓ ↓ ↓ --------------------")
        cp = subprocess.run(*args, **kwargs)
    finally:
        if decorate:
            print("-------------------- ↑ ↑ ↑ ↑ ↑ --------------------")
    return cp


def run_capture(*args, **kwargs):
    cp = subprocess.run(*args, **kwargs, capture_output=True)
    return cp
