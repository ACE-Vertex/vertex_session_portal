# Session Portal Evidence Return Reconciliation 000076V5H2

## H2 cause

000076V5H1 fixed discovery of npm, but wrapped the resolved `npm.cmd`
through `cmd.exe /d /s /c` with a quoting shape that Windows parsed
incorrectly.

The H1 Evidence simultaneously proved that the older 000073 verifier can
successfully run:

- `C:\Program Files\nodejs\npm.cmd run typecheck`
- `C:\Program Files\nodejs\npm.cmd run build`

Therefore this is not a TypeScript/build failure. It is verifier command
construction only.

## H2 repair

H2 changes verification only.

It reuses the already-proven 000073 pattern:

- on Windows resolve `npm.cmd` with `shutil.which("npm.cmd")`
- pass that absolute path directly to `subprocess.run([...], shell=False)`
- do not add a second `cmd.exe` quoting layer

It re-runs:

- 000076 static Evidence-return contracts
- npm typecheck
- npm build
- parent 000073 verifier
- Portal source immutability
- Workstation source immutability

No production Session Portal TypeScript is changed by H2.
No Workstation production source is changed by H2.
