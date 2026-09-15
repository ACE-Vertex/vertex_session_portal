# New Factory Roundtrip Smoke 000077V5

Purpose: prove the current Session Portal → Workstation → Lane → APPLY → VERIFY → Evidence → exact-origin return path with a fresh VERA05 job.

This VRA intentionally mutates only a dedicated smoke marker plus this verifier/doc.
It does not modify Session Portal production TypeScript or Workstation production Rust.

Expected live route:

VERA05 / vera-05
→ Session Portal capture
→ Human approval
→ Workstation registration
→ Workstation lane allocation
→ APPLY smoke marker
→ READ-ONLY VERIFY
→ Evidence AVAILABLE
→ Portal exact-origin return
→ vera-05 delivery
→ durable DELIVERED
→ ACK
→ RETURNED / 清算済み

Human Gate remains mandatory.
