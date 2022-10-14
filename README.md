# HPCT Cluster

> WARNING: This is a work in progress. Use at your own risk!

This package allows one to set up a cluster based on the HPCT
operators and tools.

## Steps

1. Download this package:

```
mkdir ~/tmp
git clone --recurse-submodules https://github.com/j4m-can/hpct-cluster.git
```

2. Change to bin directory:

```
cd tmp/hpct-cluster/bin
```

3. (as root) Run "check":

```
sudo ./hpct-cluster check
```

4. (as root) Run "setup" as following directions (there are some
steps to take; this sets up lxd, juju prerequisites):

```
sudo ./hpct-cluster setup
```

5. Run "check":

```
./hpct-cluster check
```

6. Run "monitor" to set up terminal with "juju status":

```
./hpct-cluster monitor
```

7. Run "prepare" and answer interview questions (this step takes a
long time when building/packaging the operators):

```
./hpct-cluster prepare
```

8. Run "deploy":

```
./hpct-cluster deploy
```

## Troubleshooting

Warning: Only delete and purge as described below if you have nothing
to lose. Otherwise, you will have to understand more about juju and
lxd and do things piecemeal.

Purging an existing juju installation:

```
snap remove juju --purge
```

Purging juju configuration under "root":

```
rm -rf /root/.local/share/juju
```

Purging juju configuration undera user:

```
rm -rf ~/.local/share/juju
```

Purging existing lxd installation:

```
snap remove lxd --purge
```
