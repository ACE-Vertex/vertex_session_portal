# VERTEX SESSION PORTAL — BETA BUILD 000041

Purpose: produce the first portable Windows x64 beta from the current healthy Session Portal baseline.

Baseline used:
- current source after the verified ChatGPT webview native-flex repair
- `npm run build`
- Electron 44.2.0
- current runtime dependency tree, including rebuilt `better-sqlite3`

Output:
- `release/beta/VertexSessionPortal-0.1.0-beta.1-win-x64/`
- executable: `VERTEX Session Portal Beta.exe`
- portable ZIP
- SHA-256 receipt
- beta build manifest

Packaging deliberately avoids adding electron-builder/electron-packager and does not require a network install.
It uses the Electron runtime already installed in the project and copies the discovered production dependency tree.

Verification includes:
1. source production build
2. compiled output presence
3. production dependency/native module packaging
4. isolated packaged-runtime smoke launch for six seconds
5. ZIP and SHA-256 generation

No application source file is modified by this artifact; only the beta build script, this release note,
and generated `release/beta` output are created.
