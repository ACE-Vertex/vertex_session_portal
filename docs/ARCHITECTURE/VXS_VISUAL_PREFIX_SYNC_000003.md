# VXS Visual Prefix Sync 000003

Purpose:
- remove the remaining human-visible `VSH` branding from the currently injected Session Portal shell
- preserve the current, newer `vertex-shell-host-bridge.ts` without replacing it

Implementation:
- modifies only `src/main/shell/vertex-shell-service.ts`
- uses Electron BrowserWindow to install a tiny DOM branding synchronizer into the existing injected shell
- converts:
  - `VERTEX SHELL` header -> `VXS`
  - `VSH ›` prompt -> `VXS ›`
  - `VSH │ ` output/system prefix -> `VXS │ `
- MutationObserver keeps future appended system lines branded as VXS

Preserved:
- current host bridge source
- VXS 0.1.0 meta command
- `vxs --version`
- internal VertexShell contracts
- Human Gate
- Workstation authority
- VRA vra/1
- Evidence contracts
