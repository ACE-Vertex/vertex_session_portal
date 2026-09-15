from pathlib import Path
import json, os, sys, traceback

ROOT = Path.cwd().resolve()
EXCLUDED = {".git","node_modules","dist","build","out","coverage",".next",".vite","target","__pycache__","runtime","EVIDENCE"}
EXTS = {".ts",".tsx",".js",".jsx",".mjs",".cjs",".json",".md",".py",".html"}

GROUPS = {
    "session_host": ["vera-01","vera-02","vera-03","vera-04","vera-05","origin_session","origin_window","source_web_contents_id"],
    "task_dispatch": ["task-dispatch","dispatch bus","dispatchbus","target-aware","roundtrip task","auto task"],
    "cross_session": ["cross-session","inter-session","session bus","session-to-session","vera-to-vera","peer vera"],
    "coordination": ["coordinator","orchestrator","supervisor","decomposer","mission router","task router","multi-vera","parallel vera"],
    "shared_state": ["shared journal","shared memory","session journal","message journal","session index","memory index","checkpoint"],
    "transcript_access": ["transcript","conversation history","chat history","message history","getmessages","get_messages","session history"],
    "unfinished": ["todo","fixme","not implemented","unimplemented","stub","placeholder","future work","planned"]
}

def clean_line(s):
    s = s.strip().replace("\x00", "")
    if len(s) > 180:
        s = s[:177] + "..."
    return s

try:
    counts = {k: 0 for k in GROUPS}
    results = []
    scanned = 0
    read_errors = 0

    for dirpath, dirnames, filenames in os.walk(str(ROOT), topdown=True, onerror=lambda _e: None):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED]

        for filename in filenames:
            p = Path(dirpath) / filename
            if p.suffix.lower() not in EXTS:
                continue
            scanned += 1

            try:
                if p.stat().st_size > 2 * 1024 * 1024:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                read_errors += 1
                continue

            low = text.lower()
            file_groups = {}
            for group, terms in GROUPS.items():
                hits = [term for term in terms if term in low]
                if hits:
                    file_groups[group] = hits[:8]

            if not file_groups:
                continue

            lines = text.splitlines()
            samples = []
            for line_no, line in enumerate(lines, 1):
                ll = line.lower()
                hit_groups = {}
                for group, terms in GROUPS.items():
                    hs = [term for term in terms if term in ll]
                    if hs:
                        hit_groups[group] = hs[:4]
                if not hit_groups:
                    continue
                samples.append({
                    "line": line_no,
                    "groups": hit_groups,
                    "text": clean_line(line)
                })
                if len(samples) >= 8:
                    break

            if samples:
                for group in file_groups:
                    counts[group] += 1
                try:
                    rp = p.relative_to(ROOT).as_posix()
                except Exception:
                    rp = str(p)
                results.append({
                    "path": rp,
                    "groups": file_groups,
                    "samples": samples
                })

    def score(row):
        weight = {
            "transcript_access": 9,
            "cross_session": 8,
            "coordination": 7,
            "task_dispatch": 6,
            "shared_state": 5,
            "session_host": 3,
            "unfinished": 2
        }
        return sum(weight.get(g, 1) for g in row["groups"])

    results.sort(key=lambda r: (-score(r), r["path"]))
    results = results[:30]

    report = {
        "schema": "vertex-session-portal/multi-vera-upper-layer-ray-1",
        "summary": {
            "target_root": str(ROOT),
            "mode": "READ_ONLY_SOURCE_OBSERVATION",
            "files_scanned": scanned,
            "read_errors": read_errors,
            "matched_files": len(results)
        },
        "group_counts": counts,
        "classification": {
            "independent_multi_vera_session_host": "PRESENT" if counts["session_host"] else "NOT_OBSERVED",
            "task_dispatch_layer": "PRESENT_OR_PARTIAL" if counts["task_dispatch"] else "NOT_OBSERVED",
            "cross_session_vera_bus": "PRESENT_OR_PARTIAL" if counts["cross_session"] else "NOT_OBSERVED",
            "upper_layer_coordinator": "PRESENT_OR_PARTIAL" if counts["coordination"] else "NOT_OBSERVED",
            "shared_session_state_or_journal": "PRESENT_OR_PARTIAL" if counts["shared_state"] else "NOT_OBSERVED",
            "live_transcript_access_between_veras": "PRESENT_OR_PARTIAL" if counts["transcript_access"] else "NOT_OBSERVED",
            "unfinished_markers": "PRESENT" if counts["unfinished"] else "NOT_OBSERVED"
        },
        "anchors": results,
        "safety": {
            "production_mutation": False,
            "network_access": False,
            "process_control": False
        },
        "next_step": "Classify IMPLEMENTED/PARTIAL/ABSENT from concrete anchors, then place System Policy Layer above session transport without duplicating existing multi-VERA machinery."
    }

    print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 ===")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 COMPLETE ===")
    raise SystemExit(0)

except Exception as exc:
    # Fail-soft so diagnostic evidence is still returned.
    error = {
        "schema": "vertex-session-portal/multi-vera-upper-layer-ray-error-1",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback_tail": traceback.format_exc().splitlines()[-12:]
    }
    print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 ===")
    print(json.dumps(error, ensure_ascii=True, indent=2))
    print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 COMPLETE ===")
    raise SystemExit(0)
