# Self-service SPHERE lifecycle

HW2 is an individual assignment. Every student creates an isolated copy of the
same fixed course topology: one OpenPLC controller node and one process/evidence
node on a private experiment link. Course staff pin the model and provisioning
payload; students control when their own eight-hour allocation starts and when
it is released.

## Local prerequisites

Install and authenticate the `mrg` CLI as described in the
[course SPHERE account setup](../../../../quickstart/sphere-account-setup.md).
The lifecycle wrapper also requires `python3`, `ssh-keygen`, and `expect` on
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
fixed environment if setup was interrupted.

## Enter the process node

```bash
./sphere/hw2-sphere status
./sphere/hw2-sphere connect
```

After `connect`, you are on the process node. Continue with:

```bash
hw2-prepare
cd ~/cs6494-hw2/hw2
./preflight.sh --require-sphere
```

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
