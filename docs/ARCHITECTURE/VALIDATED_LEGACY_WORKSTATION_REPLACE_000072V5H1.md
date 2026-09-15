# Validated Legacy Workstation Replace 000072V5H1

000072V5 production code passed TypeScript typecheck and production build.
The only failed verification item was `NO_RENDERER_PID_OR_PATH_INPUT`.

Root cause: the verifier incorrectly searched for a static HTML literal
`data-mode="replace-legacy"`, while the renderer intentionally emits the value
through a template expression:

`data-mode="${this.workstationRuntimeMismatch() ? 'replace-legacy' : 'start'}"`

H1 changes verification only.

The corrected boundary check proves that renderer source contains none of the
process-control primitives (PID lookup, netstat, PowerShell/CIM, executable path,
command line, process.kill, or direct legacy replacement function call).
Those remain owned exclusively by the main-process Workstation controller.

No production TypeScript/CSS files are changed by H1.
