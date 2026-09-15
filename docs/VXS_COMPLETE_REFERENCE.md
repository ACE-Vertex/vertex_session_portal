# VXS Complete Reference — Vertex Session Portal

> **Canonical project reference for VXS (Vertex eXecution Shell)**
>
> Project: `G:\Vertex_Project\Development\vertex_session_portal`  
> Last updated: 2026-09-15  
> Primary owner surface: Vertex Session Portal  
> Execution owner: canonical `VertexShellService`  
> Human authority: required for VERA dedicated execution  
> Current documented VXS identity: `VXS 0.1.0`

---

## 0. Purpose of this document

This file is the consolidated operational, architectural, safety, UI, VRA, Evidence, troubleshooting, and development reference for VXS inside the Vertex Session Portal project.

The intent is to avoid losing VXS knowledge across sessions and to give a future VERA, developer, reviewer, or human operator one place to understand:

- what VXS is;
- where it lives;
- how humans use it;
- how VERA uses it;
- how VRA reaches it;
- how Human Gate works;
- how PowerShell compatibility works;
- how VXS native commands work;
- how the direct loopback nerve works;
- how VXS activity is visualized;
- how the VERA persistent session workspace works;
- what is verified and what is only a design goal;
- how Evidence must be interpreted;
- what must never be bypassed.

When this file conflicts with current source or a newer VERIFIED artifact, **current source plus returned Workstation Evidence is authoritative**. Update this file after material VXS changes.

---

# 1. What VXS is

**VXS = Vertex eXecution Shell.**

VXS is the shell/execution interface used by Vertex Session Portal to expose Vertex-native commands and a compatibility execution path while preserving Human authority, provenance, verification, and Evidence.

VXS is not a second Workstation.

VXS is not a replacement Human authority layer.

VXS is not an independent raw executor that may bypass Session Portal, VRA, or Workstation policy.

The intended separation is:

```text
Human approval
    ↓
VRA transport / provenance
    ↓
Session Portal
    ↓
VERA ↔ VXS typed interface
    ↓
Human Gate
    ↓
canonical VertexShellService
    ↓
VXS native command OR compatibility backend
    ↓
result / activity / Evidence
```

For Workstation jobs, the wider flow remains:

```text
VERA
  ↓
VRA
  ↓
Session Portal Human approval
  ↓
Vertex Workstation
  ↓
lane execution
  ↓
VERIFY
  ↓
Evidence
  ↓
return queue
  ↓
origin VERA/session
```

The older short-form VXS manual also defines the separation as Human approval, VRA transport, Registry handling, Execution, Verification, and Evidence return.

---

# 2. Terminology

## 2.1 VXS

Vertex eXecution Shell. The command surface and execution interface.

## 2.2 Vertex Shell / VSH

The visible shell UI hosted by Session Portal. The prompt is shown as `VSH ›`.

The UI may contain ordinary human shell tabs such as:

```text
SHELL 1
SHELL 2
```

and VERA session workspaces such as:

```text
VERA04 · S04
```

## 2.3 VertexShellService

The canonical execution service.

Production design rule:

> **There must not be a second executor.**

VERA execution, manual VXS execution, native VXS commands, and compatibility commands must converge on the same canonical service path unless a future VERIFIED design explicitly changes this.

Important production file:

```text
src/main/shell/vertex-shell-service.ts
```

## 2.4 VERA

An AI session/agent such as `VERA04`.

VERA provenance is represented by:

```text
origin_vera    = VERA04
origin_session = vera-04
origin_window  = vera-04
```

## 2.5 VRA

A VRA is the Human-approved work/request transport and round-trip routing envelope.

It is not itself the smart executor.

For the current issuance contract:

```text
schema_version              = vra/1
authority                   = HUMAN_APPLY
routing.contract_version    = vra-routing/1
routing.return_channel      = vertex-session-portal:return-queue
routing.lane_policy         = ANY or PREFER
```

Every issuance requires fresh:

```text
artifact_id
routing.job_id
routing.correlation_id
```

Issuer provenance is immutable.

## 2.6 Evidence

Workstation execution produces durable Evidence.

Important distinction:

```text
AVAILABLE       = durable Evidence exists
RETURN_QUEUED   = return is queued/in-flight/awaiting completion or ack
RETURNED        = return workflow recorded completion/ack
```

None of those states alone prove that a human has read the result.

Transport state and human/chat visibility are separate observations.

---

# 3. Primary source files

The most important VXS/VERA integration files currently known are:

```text
src/main/shell/vertex-shell-service.ts
src/main/shell/vertex-shell-host-bridge.ts
src/main/ipc/register-vertex-shell-ipc.ts

src/shared/vera-vxs-contracts.ts

src/main/shell/vxs/vxs-command-registry.ts
src/main/shell/vxs/vera-vxs-interface.ts
src/main/shell/vxs/vera-vxs-human-authority.ts
src/main/shell/vxs/vera-vxs-vra-direct-http-nerve.ts
src/main/shell/vxs/vera-vxs-activity.ts
```

The VXS command registry composes capability modules including development, inspection, observability, source inspection, change intelligence, dependency intelligence, runtime diagnostics, orchestration, failure intelligence, job intelligence, agent context, decision, handoff, Vertex commands, capability discovery, autonomy foundation, and autonomous preparation.

The exact current command registry is always available with:

```text
vxs --help
```

or:

```text
vxs help
```

---

# 4. Manual human use

## 4.1 Opening VXS

The Vertex Shell UI is hosted inside Session Portal.

The shell supports independent human tabs. Historically these are created as:

```text
SHELL 1
SHELL 2
...
```

Each tab has its own visible CWD, command, output, history, and clipboard-oriented UI state, while process execution is single-flight at the canonical service boundary.

## 4.2 Visible shell controls

The shell UI includes:

- status;
- AUTH;
- collapse/expand;
- tab row;
- new-tab `+`;
- CWD field;
- output area;
- `VSH ›` command input;
- RUN;
- STOP;
- CLEAR;
- COPY;
- resize/move behavior.

The exact UI may evolve. Do not depend on pixel positions in automation; depend on semantic hooks and VERIFIED selectors/contracts.

## 4.3 Manual commands

A human may type VXS commands:

```text
vxs --version
vxs --help
vxs status
vxs doctor
```

or use supported compatibility commands.

Manual shell use remains distinct from the VERA dedicated route. The VERA Human Gate does not remove the human's own ability to use VXS manually.

---

# 5. Human Gate / AUTH

## 5.1 Why it exists

VERA must not silently acquire execution authority.

The dedicated VERA → VXS route is governed by a Human Gate with process-scoped state.

Current states:

```text
LOCKED
FULL
```

## 5.2 LOCKED

When LOCKED:

```text
VERA dedicated VXS requests => reject
```

Expected dedicated-route failure:

```text
VERA_VXS_HUMAN_GATE_REQUIRED
```

The direct HTTP nerve returns a locked response rather than silently executing.

## 5.3 FULL

When the human clicks AUTH and grants FULL:

- VERA dedicated requests may reach the canonical `VertexShellService`;
- canonical VXS commands are allowed through that route;
- compatibility commands may also traverse the same service;
- provenance validation remains active;
- the VRA/Human approval model remains relevant for mutation work;
- this does **not** create a second executor.

## 5.4 Process-scoped authority

The authority is intentionally process-scoped.

On Session Portal process termination/restart:

```text
FULL → LOCKED
```

Therefore the normal post-restart sequence is:

```text
restart Session Portal
  ↓
open VXS
  ↓
AUTH
  ↓
FULL
```

VERA cannot self-promote from LOCKED to FULL.

## 5.5 Security boundary

Current Human Gate/provenance validation is a structural/local boundary, not cryptographic authentication.

Do not document it as cryptographic identity proof.

A same-user local process could potentially reach loopback services while FULL. The security boundary is therefore based on:

- local loopback;
- process-scoped Human Gate;
- typed provenance validation;
- Session Portal service ownership;
- VRA/Human authority workflow;
- provider/execution policy.

---

# 6. VERA ↔ VXS typed interface

Important files:

```text
src/shared/vera-vxs-contracts.ts
src/main/shell/vxs/vera-vxs-interface.ts
```

Known interface schema family:

```text
vertex-vxs/vera-request-1
```

The dedicated interface:

- validates request structure;
- validates provenance;
- bounds returned stream data;
- delegates to the supplied canonical executor;
- must not instantiate `VertexShellService` itself;
- must not directly create a child process as an alternative executor;
- preserves request/correlation lineage.

The design principle is:

```text
VERA request
   ↓
typed interface
   ↓
executor.execute(...)
   ↓
same canonical VertexShellService
```

---

# 7. Direct VRA → VXS loopback nerve

## 7.1 Production endpoint

The production direct nerve is bound to:

```text
127.0.0.1:47834
```

Known endpoints:

```text
GET  /health
POST /v1/execute
```

Known schemas:

```text
vertex-vxs/vra-direct-health-1
vertex-vxs/vra-direct-request-1
vertex-vxs/vra-direct-response-1
```

Important file:

```text
src/main/shell/vxs/vera-vxs-vra-direct-http-nerve.ts
```

## 7.2 Why it exists

This route lets a VRA verification/client script reach the live Session Portal VXS route without creating a parallel executor.

Production path:

```text
VERA
  ↓
VRA
  ↓
Vertex Workstation verification client
  ↓
127.0.0.1:47834
  ↓
Human Gate
  ↓
executeVeraVxsRequest(...)
  ↓
canonical VertexShellService
  ↓
VXS / compatibility backend
```

## 7.3 Current boundaries

Known production constraints include:

```text
bind                = 127.0.0.1 only
CORS                = not enabled
body max            = 64 KiB
command max         = 16 KiB
cwd max             = 4096 chars
single-flight       = enforced
busy                = HTTP 429
Human Gate locked   = HTTP 423
```

Origin values are validated so that `VERAxx`, `vera-xx`, and `vera-xx` use the same suffix.

Example:

```text
VERA04 / vera-04 / vera-04
```

## 7.4 Health check

Use `/health` before execution.

The production probe expects authority data showing:

```text
mode       = FULL
granted    = true
granted_by = HUMAN
```

when VERA execution is authorized.

---

# 8. VERA activity visualization

VXS has a VERA activity layer so the human can see when an AI session is using VXS.

Important file:

```text
src/main/shell/vxs/vera-vxs-activity.ts
```

The activity model includes states equivalent to:

```text
IDLE
RUNNING
SUCCEEDED
FAILED
```

A compact UI indicator can display:

```text
VERA04 → VXS · RUNNING
VERA04 → VXS · OK
VERA04 → VXS · FAIL
```

The session-aware tab menu also identifies the origin session:

```text
VERA04 · S04
```

The session number comes from real provenance (`origin_session=vera-04`), not merely from a display guess.

Activity metadata may include:

- route;
- origin VERA;
- origin session;
- request ID;
- correlation ID;
- redacted command;
- state;
- completion/failure information.

Sensitive command material is redacted before visible display.

---

# 9. Persistent VERA session workspace

## 9.1 Purpose

The human requested that VERA04 should open a visible VXS tab/window, show what VERA is entering, keep that workspace open after completion, and continue using the same tab for later commands.

This behavior is implemented as a **persistent VERA session workspace** keyed by VERA session identity.

Current verified example:

```text
VERA04 · S04
```

## 9.2 First VERA request

On the first request from a session:

```text
VERA04 / vera-04
   ↓
VXS becomes visible if hidden
   ↓
collapsed shell expands
   ↓
dedicated VERA04 · S04 tab is created
   ↓
tab opens
   ↓
input is visible while RUNNING
   ↓
result remains visible after completion
```

## 9.3 Subsequent requests

Later requests from the same origin session reuse the same workspace:

```text
vera-04 request #1
  ↓
VERA04 · S04 tab created

vera-04 request #2
  ↓
same VERA04 · S04 tab reused

vera-04 request #3
  ↓
same tab reused
```

The design deliberately avoids creating a new VERA tab for every command.

## 9.4 Human focus behavior

After the first automatic opening, the human can switch to a normal shell tab.

If the human is viewing `SHELL 1` and VERA04 runs again:

- the `VERA04 · S04` tab remains;
- the new run is appended there;
- the VERA request does not forcibly steal human focus;
- the human can reopen the VERA tab at any time.

## 9.5 Run history

The dedicated workspace records visible run entries.

Typical display:

```text
VERA04 · S04
────────────────────────────────

VSH › vxs ps engine
RUNNING

... output ...

OK · EXIT 0
```

A later command is appended below it.

Current bounded UI history target:

```text
maximum visible run entries = 50
```

This is a UI memory bound, not a durable Evidence retention guarantee.

## 9.6 Process lifetime

The VERA workspace is a Session Portal process/UI construct.

Do not assume the visible tab survives a Portal restart unless a future VERIFIED persistence mechanism is added.

Current restart behavior still requires:

```text
restart
  ↓
Human Gate LOCKED
  ↓
human grants FULL again
```

---

# 10. Command registry

The exact current registry is authoritative through:

```text
vxs --help
```

The following command families are known from the VXS registry and verified source observations.

## 10.1 Core

```text
vxs --version
vxs --help
vxs help
vxs status
vxs doctor
```

Unknown VXS commands should return an error and direct the user to `vxs --help`.

## 10.2 Development

```text
vxs workspace
vxs scripts
vxs check
vxs format --check
vxs build
vxs test
vxs lint
vxs run <script>
vxs git help
```

These are workspace-aware development commands.

`vxs check` is intended for non-mutating code checks.

## 10.3 Inspection

```text
vxs env
vxs which <tool>
vxs tree [1-4]
vxs deps
```

## 10.4 Observability

```text
vxs logs [scope] [n]
vxs trace <job-id>
```

## 10.5 Source inspection

```text
vxs find <text> [path]
vxs inspect <path>
vxs hash <path>
vxs stat <path>
```

These commands are designed for bounded source inspection rather than uncontrolled dumping.

## 10.6 Change intelligence

```text
vxs changed
vxs diffstat
vxs refs <symbol>
vxs todo [path]
```

## 10.7 Dependency intelligence

```text
vxs imports <path>
vxs dependents <path>
vxs impact <path>
```

## 10.8 Runtime diagnostics

```text
vxs runtime
vxs port <number>
vxs process <name|pid>
vxs versions
```

Examples:

```text
vxs port 47834
vxs process vertex-session-portal
```

## 10.9 Orchestration / verification

```text
vxs preflight
vxs verify quick
vxs verify full
vxs verify changed
```

Intent:

- `quick`: fail-fast checks/tests;
- `full`: checks/tests plus build validation;
- `changed`: verify ecosystems touched by Git changes.

## 10.10 Failure intelligence

```text
vxs triage <job-id>
```

## 10.11 Job intelligence

```text
vxs jobs [n]
vxs failures [n]
vxs timeline <job-id>
```

## 10.12 Agent context

```text
vxs context
vxs context --json
```

Creates a bounded development snapshot.

## 10.13 Agent decision

```text
vxs readiness
vxs readiness --json
vxs recommend
vxs recommend --json
```

## 10.14 Agent handoff

```text
vxs handoff
vxs handoff --json
```

Bundles context/readiness/recommendations.

## 10.15 Capability discovery

```text
vxs capabilities
vxs capabilities --json
vxs describe <command>
vxs describe <command> --json
```

Use these commands to discover the safety class and machine-readable details of current VXS capabilities.

## 10.16 Autonomy foundation

```text
vxs selftest
vxs selftest --json
vxs policy
vxs policy --json
```

## 10.17 Autonomous preparation

```text
vxs prepare
vxs prepare --plan
vxs prepare --json
```

The design intent is:

```text
self-test
  ↓
plan
  ↓
safe verification
  ↓
approval point
```

It is not permission to bypass Human authority.

## 10.18 Vertex commands

```text
vxs ray [pattern]
vxs vra ...
vxs workstation ...
vxs evidence <job-id>
```

`vxs ray` is read-only workspace observation.

`vxs vra` is an alias/bridge into existing Native VRA operations.

`vxs workstation` reads Workstation control-plane state.

`vxs evidence <job-id>` reads Workstation Evidence.

---

# 11. PowerShell provider / compatibility

VXS includes a PowerShell-aware provider surface.

Known commands:

```text
vxs ps engine
vxs ps commands [pattern]
vxs ps describe <command>
vxs ps providers
vxs ps modules [pattern]
vxs ps plan <script>
vxs ps invoke <script>
```

## 11.1 `vxs ps engine`

Shows the PowerShell engine/provider identity.

This command has been used as a production direct-route smoke target.

## 11.2 `vxs ps commands`

Discovers PowerShell commands, optionally filtered by pattern.

## 11.3 `vxs ps describe`

Describes one PowerShell command/capability.

## 11.4 `vxs ps providers`

Shows PowerShell providers.

## 11.5 `vxs ps modules`

Shows modules, optionally filtered.

## 11.6 `vxs ps plan`

Plans/classifies a PowerShell script without executing it.

## 11.7 `vxs ps invoke`

Executes only when policy permits.

The initial safety model was:

```text
SAFE_READ       => may execute
mutation        => Human apply / block as policy requires
dynamic/untrusted => Human apply / block
```

The implementation uses PowerShell AST/alias/interactive/ShouldProcess-related analysis.

## 11.8 Raw compatibility commands

The VXS command registry explicitly allows non-VXS commands to continue to the configured compatibility backend.

When the VERA Human Gate is FULL, the dedicated route may submit compatibility commands through the same canonical service.

Example production witness:

```powershell
Start-Sleep -Seconds 4
Get-Process | Select-Object -First 1
```

Important:

> FULL is authorization to use the VERA → VXS route. It is not a reason to discard VRA `HUMAN_APPLY`, provider policy, provenance, verification, or recovery rules for mutation work.

---

# 12. Native provider / organ direction

VXS has been developed toward a native-first model.

High-level goal:

```text
semantic request
  ↓
provider resolver
  ↓
native VXS organ when mature/safe
  ↓
compatibility fallback when needed
```

Verified development milestones include native organ materialization, transplant/connection, Provider Resolver work, native-first route smoke, and production path probes.

Known operational families include SYSTEM and FILESYSTEM for previously verified native-route work.

PROCESS development reached scaffold/genesis stages but must not be assumed mature merely because a scaffold exists.

The long-term rule is:

> Promote repeated, safe, high-value semantics into VXS-native organs; keep compatibility backends as a controlled fallback rather than duplicating executors.

---

# 13. Safety model

## 13.1 Human is final authority

Human remains the final authority.

VXS must not redefine `HUMAN_APPLY` into an AI-granted authority.

## 13.2 No second executor

Do not implement:

```text
VERA → new child_process executor
```

beside the canonical service.

Correct architecture:

```text
VERA
  ↓
Human Gate
  ↓
typed interface
  ↓
canonical VertexShellService
```

## 13.3 Provenance

Keep:

```text
origin_vera
origin_session
origin_window
request_id
correlation_id
job_id
artifact_id
```

where applicable.

Do not rewrite issuer provenance after issuance.

## 13.4 Redaction

VXS visible activity and copied command/result material should redact common secrets including patterns such as:

```text
api_key
token
password
passwd
secret
Authorization: Bearer ...
sk-...
```

Never intentionally display real credentials in VXS session history.

## 13.5 Single-flight

The canonical service uses a single-flight/busy model.

The direct nerve reports busy rather than creating a competing execution path.

## 13.6 Rollback

When a VRA verification fails, inspect rollback Evidence before claiming production files remain modified.

Typical successful recovery:

```text
STATE=ROLLED_BACK
LOCK=NONE
```

---

# 14. Evidence interpretation contract

Always read returned Workstation Evidence in this order:

1. identity;
2. execution;
3. verification command;
4. recovery;
5. evidence durability;
6. return state;
7. first durable boundary that disagrees.

## 14.1 Success

Treat execution as Workstation-verified success when facts agree:

```text
result      = succeeded
verified    = true
success     = true
exit_code   = 0
final_state = VERIFIED
```

## 14.2 Failure

If either is true:

```text
result = failed
verified = false
```

inspect:

```text
program
args
exit_code
timed_out
stdout_path
stderr_path
rollback
write lock
```

Do not assign blame to Registry, Portal, or Workstation until the first durable disagreement is identified.

## 14.3 Write lock

`write_lock_released=true` means the verification stage no longer holds the lane write lock.

If the verify body recorded a held lock but the recovery internal reference ends in:

```text
STATE=ROLLED_BACK|LOCK=NONE
```

then the lock was released by recovery.

## 14.4 Return state

Do not call `RETURN_QUEUED` a failure.

It means queued/in-flight/awaiting completion or acknowledgement.

---

# 15. Operational runbook — human VXS

## 15.1 Basic diagnosis

```text
vxs --version
vxs status
vxs doctor
vxs runtime
vxs versions
```

## 15.2 Check the VERA direct nerve

```text
vxs port 47834
```

Expected production listener:

```text
127.0.0.1:47834
```

## 15.3 Inspect Workstation activity

```text
vxs jobs 20
vxs failures 20
vxs timeline <job-id>
vxs evidence <job-id>
```

## 15.4 Inspect project source

```text
vxs tree 2
vxs find <text> src
vxs inspect <path>
vxs hash <path>
vxs refs <symbol>
vxs impact <path>
```

---

# 16. Operational runbook — VERA dedicated VXS

Normal sequence after Portal restart:

```text
1. Session Portal starts
2. VXS Human Gate is LOCKED
3. Human opens VXS
4. Human clicks AUTH
5. Human grants FULL
6. VERA issues Human-approved VRA
7. Workstation runs VRA verification/client
8. client checks http://127.0.0.1:47834/health
9. client POSTs /v1/execute with exact VERA provenance
10. direct nerve validates request and Human Gate
11. request reaches canonical VertexShellService
12. VXS/compatibility command executes
13. VXS activity UI updates
14. VERA session workspace records command/result
15. Workstation verification returns Evidence
```

For VERA04 the visible workspace is:

```text
VERA04 · S04
```

---

# 17. Production verification milestones

The following milestones are useful when tracing why the current architecture exists.

## 17.1 Human Gate

Artifact family:

```text
vertex-session-portal-vxs-vera-human-full-access-gate-000088V4
```

Established process-scoped LOCKED/FULL authority and human-only grant behavior.

## 17.2 Direct loopback nerve

Artifact family:

```text
vertex-session-portal-vra-vxs-direct-http-nerve-000089V4
```

Established the loopback production route on port 47834 without a second executor.

## 17.3 Production bootstrap / activity

Artifact:

```text
vertex-session-portal-vxs-production-bootstrap-visual-000092V4H1
```

Evidence:

```text
ws-evidence-677c510935118452c6f698ba79242ca12f33bea4d5e5561fae401d4b8f454ac8
```

Established production bootstrap and VERA → VXS activity visualization with the corrected direct-child-process guard.

## 17.4 Full direct production route

Artifact:

```text
vertex-session-portal-vra-vxs-direct-production-probe-000093V4H2
```

Evidence:

```text
ws-evidence-f75088a30810992076a9712f7b31f582ddc0a51afc15ffa33a816e0d3ddeacf4
```

Verified production health/Human FULL, native VXS command, PowerShell engine command, and raw PowerShell compatibility execution.

## 17.5 Explicit VERA04 VRA → VXS hit

Artifact:

```text
vertex-session-portal-vera04-vra-hit-vxs-000094V4
```

Evidence:

```text
ws-evidence-4557b5da0466d0bac88fc732c6aeae4081e703ecd8559fd79e86f78c3d8f7e2b
```

Verified:

```text
VERA04
→ VRA
→ Vertex Workstation
→ 127.0.0.1:47834
→ Human AUTH Gate
→ canonical VertexShellService
→ VXS
→ vxs ps engine
→ exit 0
```

## 17.6 Session number visualization

Artifact:

```text
vertex-session-portal-vxs-vera-session-tab-visibility-000095V4H2
```

Evidence:

```text
ws-evidence-97979aaa642b9ee1a0b227e14b562a4c5c82365f453acc372cb03accfc405d23
```

Verified the session-aware tab menu with real `origin_session` provenance.

## 17.7 Human visual witness execution

Artifact:

```text
vertex-session-portal-vera04-vxs-session-visual-witness-000096V4
```

Evidence:

```text
ws-evidence-0564412fa91428776b0837a2fa498c3e36cf4db82698c3ed8366dd0ac95204de
```

Verified the production execution path while maintaining a visible RUNNING interval for human observation.

## 17.8 Persistent VERA workspace

Artifact:

```text
vertex-session-portal-vxs-vera-persistent-workspace-tab-000097V4
```

Evidence:

```text
ws-evidence-e73b655449eeb6a1d7ac195d1e3b4d6d42c8793462d8e78f09efa13bd9e47ec2
```

Verified:

```text
first request opens VXS
first request creates dedicated VERA tab
input visible during RUNNING
result visible after completion
human can switch to native tab
VERA tab remains
second request reuses same VERA tab
second request appends history
human can reopen VERA tab
no second executor
```

---

# 18. Known historical failure lessons

## 18.1 Do not test for `exec(` as a child-process guard

A previous verifier treated any `.exec(...)` as a child-process violation and false-failed because JavaScript regular expressions also use `.exec()`.

Correct guard logic must look for actual child-process imports/usage, not generic method names.

## 18.2 Windows stdout encoding

A production probe failed before HTTP because a middle-dot character could not be printed under CP932.

Verifier scripts should configure UTF-8 output before non-ASCII diagnostics.

## 18.3 Do not assume response fields

A probe incorrectly assumed the VXS response always stored visible text in one fixed `shellResult.output` field.

Inspect/validate the actual response shape or recursively search bounded result fields when the contract does not guarantee a specific string field.

## 18.4 Nested template-literal escaping

The session badge initially failed because a regular expression passed through a TypeScript template literal lost one escape layer.

When JavaScript source is embedded inside a TypeScript string/template, verify the final renderer program, not just the outer source text.

## 18.5 Static guards can false-fail

A static guard itself can be wrong.

When implementation, build, and runtime facts disagree with a guard, identify the first durable boundary rather than assuming the product code is at fault.

---

# 19. Troubleshooting

## 19.1 Port 47834 is not listening

Check:

```text
vxs port 47834
```

or Windows TCP ownership manually.

If no listener exists after a verified source change, suspect production bootstrap/build/restart before suspecting Human Gate.

AUTH does not create the listener; AUTH controls permission once the live production route exists.

## 19.2 `/health` works but execute returns locked

Human Gate is likely LOCKED.

Grant FULL manually.

## 19.3 HTTP 429

The route is busy/single-flight.

Wait for the active request to finish. Do not create another executor.

## 19.4 VERA command executes but no tab appears

Check:

- Portal restarted after the relevant build;
- `vera-vxs-activity.ts` is in the production bundle;
- `origin_session` reaches Activity;
- persistent workspace selector exists;
- human is looking at the current Session Portal process;
- the VXS host bridge is attached to that BrowserWindow.

## 19.5 Tab appears but disappears after restart

That is currently expected. The visible workspace is process/UI state, not a durable cross-restart workspace database.

## 19.6 Evidence is AVAILABLE but not visible in chat

`AVAILABLE` proves durable Evidence exists, not chat delivery.

Inspect:

```text
evidence_return_state
evidence_returned_at
```

and keep transport visibility separate from execution success.

---

# 20. Design invariants

These are the current invariants to preserve unless intentionally superseded by a newer VERIFIED design.

1. Human is final authority.
2. VERA cannot grant itself FULL.
3. Portal restart returns VERA authority to LOCKED.
4. Direct VXS HTTP binds to loopback only.
5. There is one canonical `VertexShellService`.
6. Do not add a second raw executor.
7. VERA provenance remains explicit.
8. VRA uses `HUMAN_APPLY`.
9. Workstation remains final lane allocation authority.
10. Mutation work must not silently bypass Human/VRA policy.
11. Commands/results exposed to UI must be bounded and redacted.
12. Evidence success and human visibility are different facts.
13. `RETURN_QUEUED` is not execution failure.
14. Verification failure requires rollback inspection.
15. VERA persistent tabs reuse the same origin session identity.
16. A human switching away must not cause subsequent VERA activity to steal focus.
17. Source/runtime Evidence outranks memory or assumptions.
18. `vxs --help` and `vxs capabilities --json` are the live command/capability source of truth.

---

# 21. Recommended developer checks after VXS changes

For significant VXS modifications, verification should normally include an appropriate subset of:

```text
source preflight / exact anchors
static invariants
TypeScript typecheck
npm run build
production bundle checks
Electron E2E
Human Gate LOCKED test
Human Gate FULL test
native VXS command test
PowerShell compatibility test
same canonical service assertion
no second executor assertion
activity / session provenance assertion
redaction assertion
rollback assertion on failure paths
production restart + live probe
Workstation Evidence review
```

Do not claim production behavior merely because source compilation passed.

---

# 22. Minimal recovery procedure

If a VXS production change fails:

```text
1. Read returned Evidence identity.
2. Confirm artifact/job/correlation/origin.
3. Read result/verified/final_state.
4. Read verification program/args/exit/timed_out.
5. Open verifier stdout/stderr.
6. Identify FAILURE_STAGE.
7. Inspect transaction rollback.
8. Confirm Workstation rollback and LOCK=NONE.
9. Only then issue a fresh HUMAN_APPLY repair VRA.
```

Never reuse the same artifact/job/correlation for a repair issuance.

---

# 23. Quick reference

## Human starts VERA execution

```text
Portal restart
→ VXS AUTH
→ FULL
→ VERA VRA
→ Workstation
→ 47834
→ Human Gate
→ VertexShellService
→ VXS
```

## VERA04 UI identity

```text
origin_vera    = VERA04
origin_session = vera-04
origin_window  = vera-04

visible tab:
VERA04 · S04
```

## Critical URLs

```text
http://127.0.0.1:47834/health
http://127.0.0.1:47834/v1/execute
```

## Critical commands

```text
vxs --help
vxs status
vxs doctor
vxs runtime
vxs port 47834
vxs capabilities --json
vxs ps engine
vxs ps plan <script>
vxs ps invoke <script>
vxs evidence <job-id>
```

## Success facts

```text
result=succeeded
verified=true
verification success=true
exit_code=0
final_state=VERIFIED
```

---

# 24. Source-of-truth rule

This document intentionally consolidates verified VXS knowledge, but it is not allowed to become a stale authority above the product.

Use this precedence:

```text
1. Current running behavior + returned Workstation Evidence
2. Current production source
3. Current `vxs --help` / capability registry
4. This document
5. Conversation memory / historical notes
```

Whenever a newer VERIFIED VXS change modifies behavior, update this document in the same project.

---

# 25. Maintenance note

Recommended future update policy:

```text
Every material VERIFIED VXS feature
    ↓
update this file
    ↓
include new command/API/UI behavior
    ↓
include safety boundary changes
    ↓
include new Evidence milestone
```

The goal is that a future VERA can enter the Session Portal project, read this file first, and immediately understand the VXS operating model without reconstructing it from chat history.

**End of VXS Complete Reference.**
