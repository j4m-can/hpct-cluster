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

3. Initialize (for with "edge" profile):

```
./hpct-cluster init edge
```

4. Update environment to use profile (follow output from `init` step):

```
export HPCT_PROFILE="edge"
```

5. (as root) Run "info" (replace ... appropriately):

```
cd .../tmp/hpct-cluster/bin
./hpct-cluster info -p edge
```

6. (as root) Run "setup" as following directions (there are some
steps to take; this sets up lxd, juju prerequisites):

```
cd .../tmp/hpct-cluster/bin
./hpct-cluster setup -p edge
```

7. Run "info" (expect `HPCT_PROFILE` to be set by step above):

```
./hpct-cluster info
```

Everything should be installed and set up.

8. Run "monitor" to set up terminal with "juju status":

```
./hpct-cluster monitor
```

9. Run "interview":

```
./hpct-cluster interview
```

10. Run "build":

```
./hpct-cluster build
```

This step can take some time if all the charms are being packaged from
scratch.

11. Run "info":

```
./hpct-cluster info
```

Note the status of the charms, which should all have been built and
show up as "ready".

12. Run "deploy":

```
./hpct-cluster deploy
```

This step can take some time.

## Troubleshooting

Warning: Only delete and purge as described below if you have nothing
to lose. Otherwise, you will have to understand more about juju and
lxd and do things piecemeal.

If you do not see characters typed at the console:

```
reset
```

To purge an existing juju installation:

```
snap remove juju --purge
```

To purge juju configuration under "root":

```
rm -rf /root/.local/share/juju
```

To purge juju configuration under a user:

```
rm -rf ~/.local/share/juju
```

To purge an existing lxd installation:

```
snap remove lxd --purge
```
