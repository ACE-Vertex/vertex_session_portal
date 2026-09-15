# Session Portal Evidence Return Reconciliation 000076V5H1

000076V5 production changes were applied, and all static contract checks passed.
VERIFY stopped only when Python attempted to execute a bare `npm` command with
`subprocess.run(..., shell=False)` on Windows.

The failure was:

`FileNotFoundError: [WinError 2]`

H1 changes verification only.

It now:
- resolves `npm.cmd` / `npm.exe` / `npm`
- launches `.cmd` / `.bat` through `%COMSPEC%`
- re-runs typecheck, build, parent 000073 regression, and source immutability checks

No Session Portal production TypeScript is changed by H1.
No Workstation production source is changed by H1.

The 000076 parent behavior remains:
- pull-through Workstation reconciliation
- 2500 ms Evidence-return pickup poll
- exact immutable origin routing
- durable DELIVERED before ACK
- Workstation-authoritative allocated_lane mirror
