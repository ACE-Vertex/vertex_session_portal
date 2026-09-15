# Focus / Scroll Event Ray 000076V4H1

H0 failed during verification because the Node typecheck returned exit 5 from the
Apply script. Workstation rollback completed.

H1 changes the installation strategy:

- No TypeScript production file is copied by VRA before preflight.
- The Apply script captures a baseline Node typecheck first.
- It then writes the Event Ray module and appends one side-effect import to
  `src/main/index.ts`.
- It runs Node typecheck again.
- Clean baseline requires clean post-state.
- Dirty baseline caused by parallel work is allowed only when H1 introduces
  zero new TypeScript diagnostics and zero Event-Ray diagnostics.
- Any new diagnostic triggers local restore; Workstation transaction rollback
  remains the outer safety boundary.

Electron event listener typing is version-tolerant for the current Electron 44
family, especially `console-message`. The invalid mouse-before-input assumption
from H0 is removed.

The Ray remains passive: no page text capture, no renderer layout mutation, no
VeraBrowserSession mutation, no focus/scroll API override.
