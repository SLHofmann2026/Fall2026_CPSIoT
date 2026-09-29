# Self-service SPHERE lifecycle

HW2 is an individual assignment. Every student creates an isolated copy of the
same fixed course topology: one OpenPLC controller node and one process/evidence
node on a private experiment link. Course staff pin the model and provisioning
payload; students control when their own eight-hour allocation starts and when
it is released.

## Local prerequisites

Install and authenticate the `mrg` CLI as described in the
[course SPHERE account setup](../../../../quickstart/sphere-account-setup.md).
The lifecycle wrapper also requires `python3`, OpenSSH (`ssh`), and `ssh-keygen` on
your workstation. Windows users should run it from the course-supported WSL
environment.

## Create your environment

From this HW2 directory on your workstation:

```bash
./sphere/hw2-sphere create
```

The command derives a unique name from `mrg whoami`, creates an eight-hour
realization from the pinned course model, creates a personal XDC, attaches it,
and installs the released course payload. It accepts no host, address, program,
topology, or attack parameters. Re-running `create` safely resumes your own
fixed environment if setup was interrupted. Keep this command running until it
prints **HW2 is ready** after all remote preflight checks pass. VM creation and
XDC attachment alone do not mean the lab has been installed. Provisioning takes
several minutes and does not require typing commands into its output.

## Enter the process node

```bash
./sphere/hw2-sphere status
./sphere/hw2-sphere check
./sphere/hw2-sphere connect
```

After `connect`, you are on the process node. Continue with:

```bash
hw2-prepare
cd ~/cs6494-hw2/hw2
./preflight.sh --require-sphere
```

`hw2-prepare` is installed by course provisioning at
`/usr/local/bin/hw2-prepare`; it is not a script in your repository clone. It
copies the installed payload into your writable workspace. A successful
`connect` now verifies provisioning before opening the shell.

## Recover an incomplete setup

If the home directory is empty, `hw2-prepare` is missing, or Clang/Frama-C,
network tools, or identity metadata are missing, leave the process-node shell
with `exit`. On your **workstation**, update your starter checkout and resume:

```bash
git pull --ff-only
./sphere/hw2-sphere create
./sphere/hw2-sphere check
./sphere/hw2-sphere connect
```

Then run `hw2-prepare` and the required SPHERE preflight above. Re-running
`create` provisions your existing allocation; it does not require release or
recreation and does not erase your evidence. Do not install packages, remove
your clone, or make a runs symlink to repair provisioning. Existing manually
cloned repositories are retained beside the canonical workspace. Preserve
their runs and download them before expiry. The download commands also check
the two standard manually cloned repository locations. If matching directories
exist in multiple locations, the wrapper stops so staff can reconcile them.

If setup still fails, send staff the final error and your SPHERE username.
`status` reports allocation metadata; `check` reports lab readiness. A new
allocation after expiry needs provisioning again; reconnecting to a live,
prepared allocation does not.

## Download generated work

The process node is private behind your XDC, so ordinary `scp` to `process`
does not have a direct route. You do not need to add a public key. Leave the
process-node shell and use the lifecycle wrapper from this HW2 directory on
your workstation.

Download the CFG, dependency map, tool provenance, and raw analyzer output:

```bash
./sphere/hw2-sphere download-analysis
```

Each experiment prints a path after `evidence:`. Pass only its final directory
name to download that complete evidence bundle. For example:

```bash
./sphere/hw2-sphere download-run modbus-nominal-20260920T180000Z
```

The default local destinations are `./hw2-analysis` and `./RUN_NAME`. Supply a
second argument to either command to choose a different destination. The
wrapper refuses to overwrite an existing local path. Underneath, it uses
`mrg xdc scp download` through your authenticated XDC; directly configured
SSH/SFTP is not required.

## Release resources

Download your analysis and evidence first. Then run on your workstation:

```bash
./sphere/hw2-sphere release
```

The wrapper only releases the realization and XDC derived from your authenticated
SPHERE username. Allocations also expire automatically after eight hours, but
release yours as soon as you finish so resources remain available to classmates.

## Boundaries

- Use only the resource names produced by the wrapper.
- Do not attach your XDC to another student's realization.
- Do not change the pinned model revision or shared provisioning payload.
- If creation reports exhausted capacity, release any stale allocation and try
  later; report a repeated failure to course staff.
- A new allocation is a fresh environment. Evidence is not preserved unless you
  download it before releasing or expiry.
