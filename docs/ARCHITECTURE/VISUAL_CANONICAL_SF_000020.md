# Session Portal Visual Canonical SF Restoration 000020

The approved Session Portal mock is now treated as the Visual Canonical Contract.

Changes:
- Works-orange design DNA replaced with Vertex cyan / blue / violet.
- Stronger science-fiction workstation treatment.
- Denser top command bar and bottom workstation status bar.
- Project Explorer hierarchy restored visually.
- Browser/session chrome added to Vera panes.
- 600px normal / 1200px priority width preserved.
- Whole-card click no longer expands a session.
- Explicit expand button added beside the send arrow.
- Literal SEND text removed.
- Chat textarea is vertically resizable and auto-grows to 240px.
- Enter submits; Shift+Enter inserts a line break.
- Existing SQLite, Virtual ARD, UI Control, provider and Search Vera retrieval logic is preserved.

Regression verifier:
- 3 Main Vera + 1 Search Vera.
- 4 explicit expand controls.
- 4 icon send controls.
- no literal SEND button.
- card click cannot change priority.
- all chat inputs report CSS resize=vertical.
- top command bar and explorer remain present.
