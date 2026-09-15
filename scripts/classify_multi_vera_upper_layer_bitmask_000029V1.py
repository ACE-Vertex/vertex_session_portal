from pathlib import Path
import os
import sys

ROOT = Path.cwd().resolve()
EXCLUDED = {
    ".git", "node_modules", "dist", "build", "out", "coverage",
    ".next", ".vite", "target", "__pycache__", "runtime", "EVIDENCE"
}
EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".md", ".py", ".html"}

GROUPS = {
    1:  ["vera-01", "vera-02", "vera-03", "vera-04", "vera-05",
         "origin_session", "origin_window", "source_web_contents_id"],
    2:  ["task-dispatch", "dispatch bus", "dispatchbus",
         "target-aware", "roundtrip task", "auto task"],
    4:  ["peer relay", "peer-relay", "vera-to-vera",
         "session-to-session", "cross-session", "inter-session"],
    8:  ["transcript", "conversation history", "chat history",
         "message history", "session history", "getmessages", "get_messages"],
    16: ["coordinator", "orchestrator", "supervisor",
         "decomposer", "mission router", "task router",
         "multi-vera", "parallel vera"],
    32: ["shared journal", "session journal", "message journal",
         "session index", "memory index", "shared memory"]
}

seen = {bit: False for bit in GROUPS}

for dirpath, dirnames, filenames in os.walk(str(ROOT), topdown=True, onerror=lambda _e: None):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDED]

    for filename in filenames:
        path = Path(dirpath) / filename
        if path.suffix.lower() not in EXTS:
            continue

        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue

        for bit, terms in GROUPS.items():
            if not seen[bit] and any(term in text for term in terms):
                seen[bit] = True

mask = sum(bit for bit, present in seen.items() if present)

print(f"MULTI_VERA_FEATURE_MASK={mask}")
print(f"BIT1_SESSION_HOST={str(seen[1]).upper()}")
print(f"BIT2_TASK_DISPATCH={str(seen[2]).upper()}")
print(f"BIT4_CROSS_SESSION_PEER_RELAY={str(seen[4]).upper()}")
print(f"BIT8_TRANSCRIPT_ACCESS={str(seen[8]).upper()}")
print(f"BIT16_COORDINATOR={str(seen[16]).upper()}")
print(f"BIT32_SHARED_JOURNAL_INDEX={str(seen[32]).upper()}")

sys.exit(0)
