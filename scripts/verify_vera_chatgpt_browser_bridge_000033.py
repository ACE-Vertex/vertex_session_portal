from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def require(name: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f"{name}=FAIL")
    print(f"{name}=PASS")

print("VERTEX SESSION PORTAL / VERA CHATGPT BROWSER BRIDGE VERIFY 000033")
print(f"ROOT={ROOT}")

contracts = read("src/shared/contracts.ts")
main = read("src/main/index.ts")
frame = read("src/renderer/src/components/MainFrame/MainFrame.ts")
browser = read("src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts")
browser_css = read("src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css")
explorer = read("src/renderer/src/components/Explorer/Explorer.ts")

require(
    "VERA_BROWSER_CONTRACT",
    "VERA_BROWSER_SESSION_CONTRACT" in contracts
    and "transport: 'CHATGPT_WEB'" in contracts
    and "providerFallbackForVera: 'NO'" in contracts,
)
require(
    "NO_EXTERNAL_COOKIE_IMPORT_CONTRACT",
    "cookieImportFromExternalBrowsers: 'NO'" in contracts,
)
require(
    "NO_DOM_EXTRACTION_CONTRACT",
    "automatedDomExtraction: 'NO'" in contracts,
)
require(
    "WEBVIEW_ENABLED",
    "webviewTag: true" in main,
)
require(
    "PERSISTENT_SHARED_CHATGPT_PARTITION",
    "persist:vertex-vera-chatgpt" in main
    and "persist:vertex-vera-chatgpt" in browser,
)
require(
    "INITIAL_CHATGPT_ATTACH_GUARD",
    "url.hostname === 'chatgpt.com'" in main
    and "params.partition !== VERA_CHATGPT_PARTITION" in main,
)
require(
    "REMOTE_NODE_DISABLED",
    "webPreferences.nodeIntegration = false" in main
    and "webPreferences.contextIsolation = true" in main
    and "webPreferences.sandbox = true" in main
    and "delete webPreferences.preload" in main,
)
require(
    "HTTPS_NAVIGATION_GUARD",
    "isHttpsNavigation" in main
    and "will-navigate" in main
    and "setWindowOpenHandler" in main,
)
require(
    "MAIN_LANES_RENDER_VERA_BROWSER",
    "<vera-browser-session" in frame
    and "</vera-browser-session>" in frame,
)
require(
    "SEARCH_VERA_PRESERVED",
    "<search-vera" in frame,
)
require(
    "CHATGPT_HOME",
    "const CHATGPT_HOME = 'https://chatgpt.com/'" in browser,
)
require(
    "SHARED_ACCOUNT_INDEPENDENT_THREAD",
    "SHARED ACCOUNT · INDEPENDENT THREAD" in browser,
)
require(
    "PER_LANE_LAST_THREAD",
    "vertex.vera.browser.last-url." in browser
    and "window.localStorage.setItem" in browser,
)
require(
    "BROWSER_NAV_CONTROLS",
    'data-action="back"' in browser
    and 'data-action="forward"' in browser
    and 'data-action="reload"' in browser
    and 'data-action="home"' in browser,
)
require(
    "PRIORITY_EXPAND_PRESERVED",
    "vertex-session-priority" in browser
    and 'data-action="expand"' in browser,
)
require(
    "PANE_RESIZE_PRESERVED",
    "resizeRail" in browser
    and "--session-user-width" in browser_css,
)
require(
    "ASSISTANT_UI_PRESERVED",
    "AI ASSISTANT" in explorer
    and "NO ASSISTANT" in explorer,
)
require(
    "FOOTER_CHATGPT_PRIMARY",
    "CHATGPT BROWSER · PERSISTENT ACCOUNT SESSION" in frame
    and "LEGACY CHAT ENGINE" not in frame,
)
require(
    "PROJECT_TREE_NOT_MODIFIED_BY_000033",
    "PROJECT_TREE_RESERVED" not in browser
    and "Project Explorer Tree" not in browser,
)

print("RUN=npm.cmd run build")
result = subprocess.run(
    ["npm.cmd", "run", "build"],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if result.returncode != 0:
    text = result.stdout.decode("utf-8", errors="replace")
    safe = text.encode("ascii", errors="backslashreplace").decode("ascii")
    print(safe[-12000:])
    raise SystemExit(result.returncode)

print("BUILD=PASS")
print("VERTEX_SESSION_PORTAL_VERA_CHATGPT_BROWSER_BRIDGE_000033=PASS")
