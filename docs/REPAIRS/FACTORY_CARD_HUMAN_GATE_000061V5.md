# Session Portal Factory Card / Human Gate 000061V5

Human-facing Dispatch Bay refinement.

- Keep card removal available under DETAILS with confirmation.
- Replace native Workstation dispatch confirm with a Portal-themed modal.
- Modal shows the VRA/job title and explicit OK / キャンセル actions.
- ESC or backdrop click cancels.
- Map internal states to factory vocabulary:
  未発注 → 発注済み → 作業中 → 検証済み → 返却中 → 清算済み
- Failure/rejection/delivery uncertainty maps to 要確認.
- Keep exact internal SYSTEM STATUS in DETAILS for audit.
- Footer shows 未発注 / 発注済み / 清算済み counts.
- Human Gate, Evidence return/ACK, keyed card identity, quiet EXPORT success, and Path-hidden contracts remain.
- No Workstation production source is modified.
- Hot update only; no stop/restart command.
