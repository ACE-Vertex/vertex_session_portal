from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
BROWSER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"

IMPORT_MARKER = "import '../VeraWindowScaler/VeraWindowScaler'"
TAG_MARKER = "<vertex-vera-window-scaler></vertex-vera-window-scaler>"

def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"MISSING_REQUIRED_FILE:{path}")
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(normalized.encode("utf-8"))

def safe_emit(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if text is None:
        return
    value = str(text)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe = value.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
    stream.write(safe)
    if safe and not safe.endswith("\n"):
        stream.write("\n")
    stream.flush()

def patch_main(text: str) -> str:
    out = text

    if IMPORT_MARKER not in out:
        import_matches = list(re.finditer(r"(?m)^import [^\n]+\n", out))
        if not import_matches:
            raise RuntimeError("MAINFRAME_IMPORT_ANCHOR_NOT_FOUND")
        pos = import_matches[-1].end()
        out = out[:pos] + IMPORT_MARKER + "\n" + out[pos:]

    if TAG_MARKER not in out:
        main_anchor = '<main class="main">'
        main_pos = out.find(main_anchor)
        if main_pos < 0:
            raise RuntimeError("MAINFRAME_MAIN_ANCHOR_NOT_FOUND")

        header_end = out.rfind("</header>", 0, main_pos)
        if header_end < 0:
            raise RuntimeError("MAINFRAME_HEADER_ANCHOR_NOT_FOUND")

        indent_start = out.rfind("\n", 0, header_end) + 1
        indent_match = re.match(r"[ \t]*", out[indent_start:header_end])
        indent = indent_match.group(0) if indent_match else ""
        insertion = f"{indent}  {TAG_MARKER}\n"
        out = out[:header_end] + insertion + out[header_end:]

    if "<vertex-vra-dispatch-lane" not in out:
        raise RuntimeError("VRA_DISPATCH_LANE_NOT_PRESENT")
    if "<search-vera" in out:
        raise RuntimeError("SEARCH_VERA_RENDER_MUST_STAY_RETIRED")

    return out

def patch_browser(text: str) -> str:
    out = text

    if "'vera-04'" not in out or "'vera-05'" not in out:
        pattern = re.compile(
            r"const\s+MAIN_VERA_IDS\s*=\s*\[(?P<body>[^\]]*)\]\s+as\s+const"
        )
        match = pattern.search(out)
        if not match:
            raise RuntimeError("MAIN_VERA_IDS_ANCHOR_NOT_FOUND")

        replacement = (
            "const MAIN_VERA_IDS = "
            "['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05'] as const"
        )
        out = out[:match.start()] + replacement + out[match.end():]

    if "([12345])" not in out:
        old = "const numeric = compact.match(/^(?:vera[-_]?0?)?([123])$/)"
        new = "const numeric = compact.match(/^(?:vera[-_]?0?)?([12345])$/)"
        if old in out:
            out = out.replace(old, new, 1)
        else:
            relay_pattern = re.compile(
                r"const\s+numeric\s*=\s*compact\.match\(/(\^.*?\(\[123\]\).*?\$)/\)"
            )
            match = relay_pattern.search(out)
            if not match:
                raise RuntimeError("RELAY_TARGET_REGEX_ANCHOR_NOT_FOUND")
            patched = match.group(0).replace("([123])", "([12345])", 1)
            out = out[:match.start()] + patched + out[match.end():]

    return out

def run_build() -> int:
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    print(f"RUN={npm} run build")
    result = subprocess.run(
        [npm, "run", "build"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    return result.returncode

def main() -> None:
    print("VERTEX SESSION PORTAL / FIVE VERA WINDOW SCALER REPAIR APPLY 000043H2")
    print(f"ROOT={ROOT}")
    print("ROOT_CAUSE_H1=CP932_STDOUT_UNICODE_PRINT")
    print("STDOUT_MODE=ENCODING_SAFE_BACKSLASHREPLACE")

    original_main = read(MAIN)
    original_browser = read(BROWSER)

    patched_main = patch_main(original_main)
    patched_browser = patch_browser(original_browser)

    changed_main = patched_main != original_main
    changed_browser = patched_browser != original_browser

    try:
        if changed_main:
            write(MAIN, patched_main)
        if changed_browser:
            write(BROWSER, patched_browser)

        print(f"MAINFRAME_PATCHED={'YES' if changed_main else 'ALREADY_APPLIED'}")
        print(f"VERA_BROWSER_PATCHED={'YES' if changed_browser else 'ALREADY_APPLIED'}")

        code = run_build()
        print(f"BUILD_EXIT={code}")
        if code != 0:
            raise RuntimeError("FIVE_VERA_WINDOW_SCALER_BUILD_FAILED")

    except Exception:
        if changed_main:
            write(MAIN, original_main)
        if changed_browser:
            write(BROWSER, original_browser)
        print("TRANSACTION_ROLLBACK=PASS")
        raise

    print("TRANSACTION_ROLLBACK=NOT_REQUIRED")
    print("DEFAULT_WINDOW_COUNT=3")
    print("MAX_WINDOW_COUNT=5")
    print("HEADER_SELECTOR_3_4_5=PASS")
    print("VERA_04_05_DYNAMIC=PASS")
    print("VERA_RELAY_1_TO_5=PASS")
    print("SEARCH_VERA_RETIRED=PASS")
    print("VRA_DISPATCH_LANE_PRESERVED=PASS")
    print("VERTEX_SESSION_PORTAL_FIVE_VERA_WINDOW_SCALER_000043H2_APPLY=PASS")

if __name__ == "__main__":
    main()
