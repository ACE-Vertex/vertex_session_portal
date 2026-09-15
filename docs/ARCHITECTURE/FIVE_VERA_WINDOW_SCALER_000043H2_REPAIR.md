# Five Vera Window Scaler 000043H2 — CP932 Output Repair

## Evidence-backed root cause

000043H1 successfully patched both MainFrame and VeraBrowserSession, then invoked `npm.cmd run build`.
The repair script failed while printing captured build stdout because the Works Python process used CP932 and Vite emitted Unicode check marks.

The exception triggered the transaction rollback, which correctly restored the two patched TS files. Therefore the subsequent static verifier reported the expected missing header/relay changes.

## Repair

- Preserve H1's Python-version-safe UTF-8 `write_bytes()` path.
- Add `safe_emit()` using the active stdout/stderr encoding with `backslashreplace`.
- Replace raw `print(result.stdout)` / raw stderr printing in both apply and base verifier.
- Re-apply the intended MainFrame and VeraBrowserSession patches.
- Run the original 000043 verifier after apply.
