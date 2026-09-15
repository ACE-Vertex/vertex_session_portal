# VXS Runtime Diagnostics Capability Pack 000016

Adds read-only local runtime diagnostics:

- `vxs runtime`
- `vxs port <number>`
- `vxs process <name|pid>`
- `vxs versions`

Windows adapters:
- TCP observation via `netstat.exe -ano -p tcp`
- process observation via `tasklist.exe /FO CSV /NH`
- tool version probes via existing executables

Safety:
- no taskkill
- no Stop-Process
- no shutdown/restart
- no socket mutation
- no process mutation
- bounded output
- port validated to 1..65535
- process query character validation

`vxs runtime` also observes whether Workstation 127.0.0.1:47832 appears to be
listening, but it does not start or restart the service.
