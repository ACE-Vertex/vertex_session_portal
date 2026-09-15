# VXS Capability Discovery Pack 000024

Adds machine-discoverable command registry access:

- `vxs capabilities`
- `vxs capabilities --json`
- `vxs describe <command>`
- `vxs describe <command> --json`

Schemas:
- `vxs-capabilities/1`
- `vxs-capability/1`

Each capability exposes:
- name
- aliases
- usage
- summary
- safety_class
- requires_human_gate
- automatic_execution

Safety classes:
- OBSERVE
- EXECUTE_LOCAL
- HUMAN_GATED

The discovery module receives the live command registry through a callback, so
the catalog describes the actual registered VXS commands rather than a copied
static list.

This capability performs no command execution, filesystem mutation, HTTP POST,
retry, reexecution, or Human Gate bypass.
