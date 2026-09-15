from __future__ import annotations
import time

LABEL = "A"
HOLD_SECONDS = 60

print(f"FIVE_LANE_LAMP_PROBE={LABEL}")
print(f"HOLD_SECONDS={HOLD_SECONDS}")
print("EXPECTED_RESULT=SUCCESS")
print("PURPOSE=HEADER_LANE_ACTIVE_LAMP_OBSERVATION")
print("BEGIN_HOLD", flush=True)
time.sleep(HOLD_SECONDS)
print("END_HOLD", flush=True)
print(f"PROBE_{LABEL}=PASS", flush=True)
