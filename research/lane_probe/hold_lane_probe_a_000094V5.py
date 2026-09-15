from __future__ import annotations
import os, time, datetime

LABEL = "PROBE_A"
HOLD_SECONDS = 40

def emit(value: object) -> None:
    text = str(value).encode("ascii", errors="backslashreplace").decode("ascii")
    print(text, flush=True)

def main() -> int:
    emit("=== VERTEX TWO-LANE OBSERVATION A 000094V5 ===")
    emit("TARGET=vertex_session_portal")
    emit("MODE=NON_DESTRUCTIVE_VERIFY_HOLD")
    emit("PID=" + str(os.getpid()))
    emit("START_UTC=" + datetime.datetime.now(datetime.timezone.utc).isoformat())
    emit("HOLD_SECONDS=" + str(HOLD_SECONDS))
    for elapsed in range(0, HOLD_SECONDS, 5):
        emit("ALIVE_T_PLUS=" + str(elapsed))
        time.sleep(5)
    emit("ALIVE_T_PLUS=" + str(HOLD_SECONDS))
    emit("END_UTC=" + datetime.datetime.now(datetime.timezone.utc).isoformat())
    emit("PROBE_A=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
