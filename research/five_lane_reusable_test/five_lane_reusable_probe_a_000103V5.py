from __future__ import annotations
import time

LABEL = "A"
HOLD_SECONDS = 60
RUN_KIND = "REUSABLE_TEST"

print(f"FIVE_LANE_REUSABLE_TEST={LABEL}", flush=True)
print(f"HOLD_SECONDS={HOLD_SECONDS}", flush=True)
print(f"RUN_KIND={RUN_KIND}", flush=True)
print("EXPECTED_RESULT=SUCCESS", flush=True)
print("PURPOSE=SESSION_PORTAL_HEADER_LANE_LAMP_OBSERVATION", flush=True)
print("BEGIN_HOLD", flush=True)
time.sleep(HOLD_SECONDS)
print("END_HOLD", flush=True)
print(f"PROBE_{LABEL}=PASS", flush=True)
