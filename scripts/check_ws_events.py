#!/usr/bin/env python3
"""Quick check if WebSocket events are being published."""

import sys

sys.path.insert(0, "C:/noc_project/UNOC/unoc")

from backend import events

counts = events.get_event_counts()
print("\n=== EVENT COUNTS ===")
for k, v in sorted(counts.items()):
    print(f"  {k}: {v}")

dm = counts.get("deviceMetricsUpdated", 0)
lm = counts.get("linkMetricsUpdated", 0)

print(f"\n{'✅' if dm > 0 else '❌'} deviceMetricsUpdated: {dm} events")
print(f"{'✅' if lm > 0 else '❌'} linkMetricsUpdated: {lm} events")

if dm > 0 and lm > 0:
    print("\n🎉 WebSocket events ARE being published!")
else:
    print("\n⚠️ WebSocket events NOT being published - check v2_runner.py")
