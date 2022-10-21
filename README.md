# HPCT Cluster

> WARNING: This is a work in progress. Use at your own risk!

This package allows one to set up a cluster based on the HPCT
operators and tools.

## Preparation

### Oracle 8

As root:

```
yum install git python3-PyYAML python38
```

### Ubuntu

No special steps are required after base install.

## Steps

1. Download this package:

```
mkdir ~/tmp
cd tmp
git clone --recurse-submodules https://github.com/j4m-can/hpct-cluster.git
```

2. Change to bin directory:

```
cd hpct-cluster/bin
```

3. Initialize (for with "cluster" profile):

```
./hpct-cluster init cluster
```

3. (as root) Run "check" (replace ... appropriately):

```
cd .../tmp/hpct-cluster/bin
./hpct-cluster check
```

4. (as root) Run "setup" as following directions (there are some
steps to take; this sets up lxd, juju prerequisites):

```
cd .../tmp/hpct-cluster/bin
./hpct-cluster setup
```

5. Run "check":

```
./hpct-cluster check
```

Everything should be installed and set up.

6. Run "monitor" to set up terminal with "juju status":

```
./hpct-cluster monitor
```

7. Run "interview":

```
./hpct-cluster interview
```

8. Run "build":

```
./hpct-cluster build
```

This step can take some time if all the charms are being packaged from
scratch.

9. Run "check":

```
./hpct-cluster check
```

Note the status of the charms, which should all have been built and
show up as "ready".

10. Run "deploy":

```
./hpct-cluster deploy
```

This step can take some time.

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
