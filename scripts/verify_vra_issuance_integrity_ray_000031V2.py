from __future__ import annotations

import json
import os
import sqlite3
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

IDENTITY_FIELDS = [
    "artifact_id",
    "job_id",
    "correlation_id",
    "origin_vera",
    "origin_session",
    "origin_window",
    "return_channel",
    "project_id",
    "project_name",
    "lane_policy",
    "card_kind",
    "authority",
]

PRUNE_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".next",
    "coverage", ".cache", "__pycache__", "vendor",
}

MAX_SIDECARS = 80
MAX_VRA = 120
MAX_DBS = 30
MAX_ROWS = 120


def safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def walk_files(root: Path, suffix_predicate, limit: int) -> list[Path]:
    found: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        for name in files:
            p = Path(base) / name
            try:
                if suffix_predicate(p):
                    found.append(p)
            except Exception:
                continue
    found.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return found[:limit]


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def manifest_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    routing = manifest.get("routing") if isinstance(manifest.get("routing"), dict) else {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    target = manifest.get("target") if isinstance(manifest.get("target"), dict) else {}
    return {
        "artifact_id": manifest.get("artifact_id"),
        "job_id": routing.get("job_id"),
        "correlation_id": routing.get("correlation_id"),
        "origin_vera": routing.get("origin_vera") or source.get("actor"),
        "origin_session": routing.get("origin_session"),
        "origin_window": routing.get("origin_window"),
        "return_channel": routing.get("return_channel"),
        "project_id": routing.get("project_id") or target.get("project_id"),
        "project_name": routing.get("project_name") or target.get("project_name"),
        "lane_policy": routing.get("lane_policy"),
        "card_kind": manifest.get("card_kind"),
        "authority": manifest.get("authority"),
    }


def sidecar_identity(meta: dict[str, Any]) -> dict[str, Any]:
    return {k: meta.get(k) for k in IDENTITY_FIELDS}


def extract_manifest(vra_path: Path) -> dict[str, Any] | None:
    try:
        if not zipfile.is_zipfile(vra_path):
            return None
        with zipfile.ZipFile(vra_path, "r") as zf:
            if "manifest.json" not in zf.namelist():
                return None
            obj = json.loads(zf.read("manifest.json").decode("utf-8"))
            return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def flatten_jsonish(row: dict[str, Any]) -> dict[str, Any]:
    flat = dict(row)
    for key, value in list(row.items()):
        if not isinstance(value, str):
            continue
        s = value.strip()
        if not (s.startswith("{") and s.endswith("}")):
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict):
            for k, v in obj.items():
                flat.setdefault(k, v)
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        flat.setdefault(kk, vv)
    return flat


def compare(a_name: str, a: dict[str, Any], b_name: str, b: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches = []
    for field in IDENTITY_FIELDS:
        av = a.get(field)
        bv = b.get(field)
        if av is None or bv is None:
            continue
        if av != bv:
            mismatches.append({
                "field": field,
                a_name: av,
                b_name: bv,
            })
    return mismatches


def sqlite_rows(db_path: Path, table: str) -> tuple[list[dict[str, Any]], list[str]]:
    uri = "file:" + db_path.resolve().as_posix() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=1.0)
    con.row_factory = sqlite3.Row
    try:
        cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
        rows = []
        try:
            data = con.execute(
                f"SELECT rowid AS __rowid__, * FROM {table} ORDER BY rowid DESC LIMIT ?",
                (MAX_ROWS,),
            ).fetchall()
        except sqlite3.DatabaseError:
            data = con.execute(f"SELECT * FROM {table} LIMIT ?", (MAX_ROWS,)).fetchall()
        for row in data:
            rows.append(flatten_jsonish(dict(row)))
        return rows, cols
    finally:
        con.close()


def table_names(db_path: Path) -> list[str]:
    uri = "file:" + db_path.resolve().as_posix() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=1.0)
    try:
        return [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
    finally:
        con.close()


def main() -> int:
    root = Path.cwd().resolve()

    sidecars = walk_files(
        root,
        lambda p: ".vra.meta" in p.name.lower() and p.suffix.lower() == ".json",
        MAX_SIDECARS,
    )
    vra_files = walk_files(
        root,
        lambda p: p.suffix.lower() == ".vra",
        MAX_VRA,
    )
    db_files = walk_files(
        root,
        lambda p: p.suffix.lower() in {".sqlite", ".sqlite3", ".db"},
        MAX_DBS,
    )

    vra_by_name: dict[str, list[Path]] = defaultdict(list)
    for p in vra_files:
        vra_by_name[p.name].append(p)

    sidecar_records = []
    duplicate_job_ids: dict[str, list[str]] = defaultdict(list)
    duplicate_corr_ids: dict[str, list[str]] = defaultdict(list)

    for sp in sidecars:
        meta = read_json(sp)
        if not meta:
            continue
        ident = sidecar_identity(meta)
        jid = ident.get("job_id")
        cid = ident.get("correlation_id")
        if jid:
            duplicate_job_ids[str(jid)].append(safe_rel(sp, root))
        if cid:
            duplicate_corr_ids[str(cid)].append(safe_rel(sp, root))

        manifest = None
        manifest_path = None
        manifest_mismatches = []

        candidate_names = []
        for key in ("filename", "publish_name", "staged_name"):
            v = meta.get(key)
            if isinstance(v, str) and v.lower().endswith(".vra"):
                candidate_names.append(Path(v).name)

        for name in candidate_names:
            paths = vra_by_name.get(name, [])
            if paths:
                manifest_path = paths[0]
                manifest = extract_manifest(manifest_path)
                if manifest:
                    manifest_mismatches = compare(
                        "manifest",
                        manifest_identity(manifest),
                        "sidecar",
                        ident,
                    )
                    break

        return_state = meta.get("workstation_evidence_return_state")
        evidence_state = meta.get("workstation_evidence_state")
        suspicious = (
            return_state == "RETURN_QUEUED"
            or (evidence_state == "AVAILABLE" and return_state not in {"RETURNED", None})
            or bool(manifest_mismatches)
        )

        sidecar_records.append({
            "sidecar": safe_rel(sp, root),
            "manifest": safe_rel(manifest_path, root) if manifest_path else None,
            "identity": ident,
            "workstation_registration": meta.get("workstation_registration"),
            "workstation_job_state": meta.get("workstation_job_state"),
            "workstation_evidence_state": evidence_state,
            "workstation_evidence_return_state": return_state,
            "workstation_last_error": meta.get("workstation_last_error"),
            "manifest_vs_sidecar_mismatches": manifest_mismatches,
            "suspicious": suspicious,
        })

    registry_rows: list[dict[str, Any]] = []
    vlog_rows: list[dict[str, Any]] = []
    db_observations = []

    for db in db_files:
        obs: dict[str, Any] = {
            "path": safe_rel(db, root),
            "tables": [],
            "error": None,
        }
        try:
            tables = table_names(db)
            obs["tables"] = tables
            if "vra_registry" in tables:
                rows, cols = sqlite_rows(db, "vra_registry")
                obs["vra_registry_columns"] = cols
                for r in rows:
                    r["__db__"] = safe_rel(db, root)
                registry_rows.extend(rows)
            if "vertex_vlog" in tables:
                rows, cols = sqlite_rows(db, "vertex_vlog")
                obs["vertex_vlog_columns"] = cols
                for r in rows:
                    r["__db__"] = safe_rel(db, root)
                vlog_rows.extend(rows)
        except Exception as exc:
            obs["error"] = f"{type(exc).__name__}: {exc}"
        db_observations.append(obs)

    registry_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    registry_by_artifact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in registry_rows:
        if r.get("job_id") is not None:
            registry_by_job[str(r.get("job_id"))].append(r)
        if r.get("artifact_id") is not None:
            registry_by_artifact[str(r.get("artifact_id"))].append(r)

    comparisons = []
    for record in sidecar_records:
        ident = record["identity"]
        jid = ident.get("job_id")
        aid = ident.get("artifact_id")
        rows = []
        if jid:
            rows.extend(registry_by_job.get(str(jid), []))
        if not rows and aid:
            rows.extend(registry_by_artifact.get(str(aid), []))

        reg_summary = None
        reg_mismatches = []
        if rows:
            reg = flatten_jsonish(rows[0])
            reg_summary = {
                k: reg.get(k)
                for k in (
                    "registry_id", "job_id", "artifact_id", "correlation_id",
                    "origin_vera", "origin_session", "origin_window",
                    "return_channel", "project_id", "project_name",
                    "state", "status", "evidence_id", "allocated_lane"
                )
                if k in reg
            }
            reg_mismatches = compare("sidecar", ident, "registry", reg)

        if record["suspicious"] or reg_mismatches:
            comparisons.append({
                "sidecar": record["sidecar"],
                "job_id": jid,
                "artifact_id": aid,
                "manifest_vs_sidecar_mismatches": record["manifest_vs_sidecar_mismatches"],
                "sidecar_vs_registry_mismatches": reg_mismatches,
                "registry": reg_summary,
                "return_state": record["workstation_evidence_return_state"],
                "evidence_state": record["workstation_evidence_state"],
            })

    duplicate_jobs = {k: v for k, v in duplicate_job_ids.items() if len(v) > 1}
    duplicate_corrs = {k: v for k, v in duplicate_corr_ids.items() if len(v) > 1}

    queued = [
        r for r in sidecar_records
        if r["workstation_evidence_return_state"] == "RETURN_QUEUED"
    ]
    returned = [
        r for r in sidecar_records
        if r["workstation_evidence_return_state"] == "RETURNED"
    ]

    diagnosis = []
    if duplicate_jobs:
        diagnosis.append("DUPLICATE_JOB_ID_IN_SIDECARS")
    if duplicate_corrs:
        diagnosis.append("DUPLICATE_CORRELATION_ID_IN_SIDECARS")
    if any(c["manifest_vs_sidecar_mismatches"] for c in comparisons):
        diagnosis.append("MANIFEST_TO_PORTAL_CAPTURE_IDENTITY_MUTATION")
    if any(c["sidecar_vs_registry_mismatches"] for c in comparisons):
        diagnosis.append("PORTAL_CAPTURE_TO_REGISTRY_IDENTITY_MUTATION")
    if queued and not any(
        c["manifest_vs_sidecar_mismatches"] or c["sidecar_vs_registry_mismatches"]
        for c in comparisons
    ):
        diagnosis.append("IDENTITY_INTACT_BUT_RETURN_QUEUED_PERSISTS")
    if not diagnosis:
        diagnosis.append("NO_IDENTITY_MUTATION_DETECTED_IN_VISIBLE_DURABLE_FACTS")

    report = {
        "schema": "vertex-ray/vra-issuance-integrity/1",
        "mode": "READ_ONLY",
        "project_root": str(root),
        "scope": "VERA -> VRA -> Portal Capture -> sidecar/meta -> Registry Intake",
        "workstation_mutation": "NONE",
        "counts": {
            "sidecars": len(sidecar_records),
            "vra_files": len(vra_files),
            "sqlite_files": len(db_files),
            "registry_rows": len(registry_rows),
            "vlog_rows": len(vlog_rows),
            "return_queued_sidecars": len(queued),
            "returned_sidecars": len(returned),
        },
        "diagnosis": diagnosis,
        "duplicate_job_ids": duplicate_jobs,
        "duplicate_correlation_ids": duplicate_corrs,
        "comparisons": comparisons[:30],
        "return_queued": queued[:20],
        "db_observations": db_observations,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    # Diagnostic probe succeeds if it completed safely. Findings are reported in Evidence,
    # not encoded as a failing process exit.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
