import os
import sys

sys.path.insert(0, "c:/noc_project/UNOC/unoc")
import backend.db as db  # type: ignore

print("persistence_mode env:", os.getenv("UNOC_PERSISTENCE"), "resolved:", db._persistence_mode)
