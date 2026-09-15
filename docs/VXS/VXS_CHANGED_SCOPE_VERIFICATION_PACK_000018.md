# VXS Changed-Scope Verification Pack 000018

Extends the VERIFIED orchestration layer with:

- `vxs verify changed`
- `vxs verify-plan [quick|full|changed]`

Changed mode:
1. reads `git status --short --untracked-files=normal`
2. classifies changed files into Node / Rust / Python ecosystems
3. selects only the quick verification pipeline for touched ecosystems
4. falls back conservatively to all detected ecosystems if changed files cannot
   be classified
5. returns success without execution for a clean working tree

`verify-plan` performs the same planning but never executes the pipeline.

No Git mutation, process control, source rewriting, or Workstation mutation is added.
