# VERTEX Session Portal

Vera専用のマルチセッション Agent System / Virtual ARD workspace.

## Baseline

- Electron + Chromium + TypeScript
- Vanilla Web Components + Shadow DOM
- Workstation-local SQLite
- Default: 3 Main Vera + 1 Search Vera
- Max active: 5
- Session min width: 600px
- Priority target: ~1200px
- Max width: none
- Sidebar: PROJECT / VCR / VCA
- Typed UI Control Channel
- Component-local CSS + shared design DNA

## Development

```powershell
npm install
npm run dev
```

Verification:

```powershell
npm run typecheck
npm run build
```

See `docs/ARCHITECTURE.md` and `docs/BUILD_RULES.md`.
