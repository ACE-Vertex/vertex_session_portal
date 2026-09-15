# AUTO Full Execution Authority — 000109V5H1

000109V5 failed at verifier exit 21 and was fully rolled back.

Root cause was verifier/UI-string mismatch only:
the implementation status text already said FULL EXECUTION AUTHORITY,
but the generated replacement targeted `button.title` while the actual source
uses `autoButton.title`.

H1 reapplies the same main-process execution-authority implementation and
changes the actual AUTO button title to:

`Vertex AUTO · Task Dispatch + VRA Execution Authority`

No authority model is weakened. Human AUTO arm remains the grant.
AUTO OFF, expiry, restart, old cards, scope mismatch, and ambiguity fail closed.
Workstation remains final Lane Allocation Authority.
