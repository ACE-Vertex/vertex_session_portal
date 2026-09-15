# Vertex Shell OneClip + Compound Command 000080V4C

Human UX correction after first real runtime use.

Observed friction:
- two separate submissions for `cd` then command is unreasonable
- ANSI/VT sequences pollute pasted output
- result needs a one-click route back to Vera

V4C changes only:
- Vertex Shell service
- Vertex Shell host bridge UI

## Compound command

A standalone `cd <path>` remains a persistent Vertex Shell meta-command.

If the input contains a PowerShell separator (`;`, newline, `|`, `&`), it is
passed intact to pwsh.

Example, one submission:

`cd G:\Vertex_Project\Development\vertex_session_portal; python scripts\probe_vertex_shell_runtime_000080V4B.py`

## COPY

COPY is one click.

It copies the most recent command plus its output/result. ANSI/VT control
sequences are removed before display/copy so the pasted evidence is clean.

If clipboard.writeText is unavailable, a local textarea/execCommand fallback is
used.

No Vera/agent automatic shell authority is added.
