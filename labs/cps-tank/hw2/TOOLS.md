# What the HW2 tools do for you

`preflight.sh` checks Python and released files. In the prepared SPHERE process
node, `./preflight.sh --require-sphere` also checks the supplied identity,
transport, fixed OpenPLC endpoint, and network tools. It reports the expiry
value but does not enforce the course resource deadline. Students do not need
to compile C or install dependencies on a successfully provisioned node.
`hw2-prepare` is installed at `/usr/local/bin/hw2-prepare` by the provisioning
step; it is not a repository script. If it or the tools are missing, leave the
node and resume `./sphere/hw2-sphere create` from your updated workstation
checkout. See [setup recovery](sphere/README.md#recover-an-incomplete-setup).

`analyze.sh` launches Clang's `debug.DumpCFG` and Frama-C Eva with `-deps`,
preserves their raw output, and projects those results into the course CFG and
dependency-map formats. `static_view.py` is an adapter, not a substitute C
analyzer. You must still interpret the observation-to-actuator path and the
tools' stated assumptions.

`verify_representations.sh` executes six stateful sequences through the reference, existing Python controller, compiled C, and supported ST model. Passing establishes bounded agreement on those sequences, not universal equivalence.

`run_nominal.sh` selects the real OpenPLC/Modbus runner only when
`HW2_TRANSPORT=modbus_tcp`; otherwise it selects the labeled local model. Both
begin with a fresh tank model and evaluate the provided physical property.

`run_spoof.sh` uses the same transport selector for a fixed, bounded
reported-level manipulation. Inspect the released runner constants and
transformation before writing your prediction; this page deliberately does not
pre-summarize them. The manipulation does not directly set the valve, tank
level, or PLC program. On SPHERE, the fixed process client writes the resulting
value to OpenPLC with Modbus TCP and captures the traffic. In the local
fallback, `run_case.sh sensor_spoof` models the exchange and produces no pcap.

`show_network.sh RUN_DIRECTORY` re-decodes a SPHERE run's `network.pcap` with
`tshark` and prints a compact readable projection. The bundle's
`modbus_trace.csv` is a saved, more detailed projection of that same pcap, so
similar rows and equal packet counts are expected. Neither is an independent
second capture. For Part B, select representative transactions rather than
classifying every repeated scan.

`search.sh` runs a transparent finite Cartesian grid over selected initial
levels, attack starts, and sensor biases. Part D asks you to vary one dimension,
so pass one fixed value for each of the other two; otherwise the multi-value
defaults also vary them. For example,
`./search.sh --initial 50 --start 8 --bias -20 -35 -50` varies only bias.

The result CSV includes both inputs and outcomes. `spoof_after_s` echoes the
selected `--start` value. `first_violation_s` is the earliest sampled time at
which process truth reaches the 90% high-high threshold and is blank for a
passing case. `physical_property` is the finite-run `PASS`/`FAIL` verdict for
`always(true_level_pct < 90)`. These columns support your table or plot; they
are not additional command-line parameters. The tool remains bounded search,
not a production fuzzer or proof engine.

`program_plane_demo.sh` compares hashes and bounded safety results for known baseline and modified ST files. It is offline and opens no network connection.

`collect.sh` checks required files, columns, schema version, and checksums;
for SPHERE bundles it additionally requires a nonempty pcap and consistent
derived Modbus trace. Passing validation means the bundle is structurally
complete and unchanged since collection—not that its scientific
interpretation is correct.

`property_oracle.py` evaluates `always(true_level_pct < 90)` over the finite process trace. It is deliberately ordinary Python so you can inspect and adapt the predicate. A passing finite run is not proof of universal safety.

`reset.sh` also selects by transport. The local path clears only known
transient scaffold state. The SPHERE path writes the fixed 56% initialization
value, waits for a real OpenPLC scan, and verifies that coil 0 is CLOSED so
retained hysteresis state cannot leak into the next run. Both retain evidence.

The scripts intentionally automate setup, execution, timestamps, packaging, and basic validation. They do not answer why the property matters, whether the evidence is sufficient for your claim, what caused a violation, whether modeled network rows were real packets, or what stronger claim remains unsupported.
