# Validated Legacy Workstation Replace 000072V5

The live video proves Portal 000070 is working as designed:

`WORKSTATION LEGACY · RESTART REQUIRED`

The spinning mouse cursor over the starter is not a running build. It came from the CSS
contract `cursor: wait` on the intentionally disabled mismatch button.

000072 makes that Human control actionable without introducing a blind kill.

On explicit `REPLACE LEGACY` click only:

1. confirm a listener is occupying `127.0.0.1:47832`;
2. discover its PID from Windows TCP listener state;
3. inspect the PID's executable path and command line;
4. require `vertex.exe` / `vertex-workstation.exe`;
5. require the executable to live under the Workstation project or Portal workstation-server slot;
6. require command line `workstation serve` + exact loopback bind;
7. terminate only that validated PID;
8. wait until the control plane is offline;
9. launch current Workstation source via isolated Portal-managed Cargo target;
10. let normal runtime/recovery identity verification decide ONLINE.

No renderer-controlled PID/path/command is accepted.
No automatic process replacement occurs during passive health polling.
Session Portal and Workstation remain separate processes.
