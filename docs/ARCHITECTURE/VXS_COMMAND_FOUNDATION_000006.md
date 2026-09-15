# VXS Command Foundation 000006

## Purpose

Turn VXS from a single embedded command shell into the common execution entry
for multiple Vertex development workflows.

## Architecture

VXS Parser
  -> Command Registry
  -> Workspace Detector
  -> Command / Capability implementation
  -> native Vertex capability or compatibility backend

This artifact introduces the registry boundary before the command surface grows.

## Implemented commands

- `vxs --version` — existing identity command, preserved
- `vxs --help` — list current native VXS commands
- `vxs help` — alias
- `vxs status` — detect and describe the current workspace
- `vxs doctor` — diagnose core development tools required by the workspace

Unknown `vxs ...` commands fail inside VXS instead of silently falling through
to PowerShell.

Non-VXS commands continue to the existing `pwsh.exe` compatibility backend.

## Workspace Detector

Detects nearest workspace markers for:

- Node / package.json
- Rust / Cargo.toml
- Python / pyproject.toml, requirements.txt, setup.py
- mixed workspaces
- generic directories

Node workspace details include:

- package manager: npm / pnpm / yarn
- package name/version
- framework hints: Electron, Vue, React, TypeScript, Vite, electron-vite, Quasar
- package scripts

## Doctor semantics

Doctor emits PASS / WARN / FAIL lines so the existing VXS editor color
semantics can render:

- PASS -> green
- WARN -> orange
- FAIL -> red

Required tools are selected from the detected workspace.

## Branding cleanup

The human-visible runtime banner:

`VERTEX SHELL 000080V4G · SHELL N`

is normalized to:

`VXS 0.1.0 · SHELL N`

without replacing the newer production host bridge source.

## Preserved invariants

- VXS Settings + tab close 000005
- VXS 0.1.0
- `vxs --version`
- Human Gate / HUMAN_APPLY
- Workstation lane authority
- vra/1
- current host bridge source
- existing PowerShell compatibility backend
