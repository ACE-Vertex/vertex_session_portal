from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def need(label, condition):
    if not condition:
        raise RuntimeError(label)
    print(label + "=PASS")

def main():
    explorer = text("src/renderer/src/components/Explorer/Explorer.ts")
    css = text("src/renderer/src/components/Explorer/Explorer.css")
    db = text("src/main/storage/workstation-db.ts")
    preload = text("src/preload/index.ts")

    print("VERTEX SESSION PORTAL / VCR CARD + MODAL VERIFY 000030")
    print("ROOT=" + str(ROOT))

    need("VCR_CARD_RENDER", 'class="resultCard vcrCard"' in explorer)
    need("VCR_DOUBLE_CLICK_OPEN", "card.addEventListener('dblclick', openCard)" in explorer)
    need("VCR_ADD_BOTTOM_CONTROL", 'data-action="add-vcr"' in explorer and 'vcrAddGlyph">⊕' in explorer)
    need("VCR_MODAL_PRESENT", 'class="vcrModalBackdrop"' in explorer and 'role="dialog"' in explorer)
    need("VCR_MODAL_OUTSIDE_CLICK_CLOSE", "event.target === event.currentTarget" in explorer)
    need("VCR_MODAL_ESCAPE_CLOSE", "event.key === 'Escape'" in explorer and "this.closeVcrEditor()" in explorer)
    need("VCR_MODAL_CLOSE_BUTTON", 'data-action="close-vcr"' in explorer)
    need("VCR_MODAL_FADE_SCALE", "@keyframes vcrModalIn" in css and "@keyframes vcrBackdropIn" in css and "scale(.965)" in css)
    need("VCR_EDIT_FIELDS", 'name="title"' in explorer and 'name="category"' in explorer and 'name="status"' in explorer and 'name="body"' in explorer)
    need("VCR_EXISTING_KEY_LOCKED", "${editing ? 'readonly' : ''}" in explorer)
    need("VCR_EXISTING_UPSERT_API", "window.vertexPortal.upsertVcrEntry" in explorer and "upsertVcrEntry" in preload)
    need("VCR_APPEND_ONLY_DB_PRESERVED", "const nextRevision = row.revision + 1" in db and "INSERT INTO vcr_revision" in db)
    need("EXPLORER_NO_HORIZONTAL_SCROLL_PRESERVED", "overflow-x:hidden;" in css)
    need("AI_LANE_UI_PRESERVED", 'data-action="add-lane"' in explorer and "Five independent LLM lanes" in explorer)

    # The intentionally temporary project-tree stub must remain untouched for dedicated 000031.
    need(
        "PROJECT_TREE_RESERVED_FOR_000031",
        "<strong>vertex_session_portal</strong>" in explorer
        and '<span>renderer</span>' in explorer
        and '<span>package.json</span>' in explorer
    )

    print("RUN=npm.cmd run build")
    run = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if run.returncode != 0:
        sys.stdout.write(run.stdout.encode("ascii", "backslashreplace").decode("ascii"))
        sys.stderr.write(run.stderr.encode("ascii", "backslashreplace").decode("ascii"))
        raise SystemExit(run.returncode)

    print("BUILD=PASS")
    print("VERTEX_SESSION_PORTAL_VCR_CARD_MODAL_000030=PASS")

if __name__ == "__main__":
    main()
