# VXS PowerShell Engine Provider 000067V3

## Purpose

Promote PowerShell from a compatibility shell into a structured engine provider inside Vertex eXecution Shell (VXS).

## Architecture

`VERA/Human -> VXS Command Registry -> VXS PowerShell Engine Adapter -> System.Management.Automation -> Windows/Providers`

The adapter consumes PowerShell engine metadata rather than treating every operation as opaque text:

- Parser / AST (`System.Management.Automation.Language.Parser`)
- Command discovery (`Get-Command`, `CommandInfo`)
- Parameter / safety metadata (`CommandMetadata`)
- Provider model (`Get-PSProvider`, `Get-PSDrive`)
- Module discovery (`Get-Module -ListAvailable`)
- Runtime identity (PowerShell/.NET/LanguageMode/Runspace/assembly)

## Commands

- `vxs ps engine` — engine/runtime identity
- `vxs ps commands [pattern]` — discover commands
- `vxs ps describe <command>` — command metadata + safety signals
- `vxs ps providers` — providers/drives
- `vxs ps modules [pattern]` — modules/exported commands
- `vxs ps plan <script>` — AST analysis only
- `vxs ps invoke <script>` — executes only when classified `SAFE_READ`

## Safety boundary

This pack does **not** grant arbitrary mutation authority. PowerShell abilities may be discovered and described, but mutation, dynamic invocation, redirection, assignment, member invocation, untrusted command types, and non-read-safe verbs are classified `HUMAN_GATED` / `HUMAN_APPLY`. `vxs ps invoke` returns `BLOCKED_HUMAN_APPLY` instead of executing them.

The existing VXS compatibility backend remains in place so current commands continue to work while the engine-provider route is adopted incrementally.

## Phase boundary

This is Engine Provider Phase 1. It establishes a typed/structured seam without rewriting every existing VXS capability. Later packs can route existing `vxs port`, `vxs process`, environment inspection and other PowerShell-backed capabilities through the provider one by one.
