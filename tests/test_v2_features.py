"""
tests/test_v2_features.py
-------------------------
End-to-end regression test for HM-Debugger v2:
- hm-start
- hs (hm-tour stepping)
- hn (hm-next-rd auto-diff)
- hi (context-aware inspection)
- hg (grid)
- hm-menu
"""

import gdb

print("\n--- TEST V2: HM-START ---")
gdb.execute("hm-start 0 0")

print("\n--- TEST V2: HM-MENU ---")
gdb.execute("hm-menu")

print("\n--- TEST V2: RUNNING TO FIRST BREAKPOINT ---")
gdb.execute("run")

print("\n--- TEST V2: HI (CONTEXT INSPECT) ---")
gdb.execute("hi")

print("\n--- TEST V2: HN (NEXT RD CANDIDATE WITH AUTO-DIFF) ---")
gdb.execute("hn")

print("\n--- TEST V2: HG (GRID) ---")
gdb.execute("hg")

print("\n--- TEST V2: HS (PIPELINE TOUR STEPPING) ---")
gdb.execute("hs")

print("\n>>> ALL V2 FEATURES VERIFIED SUCCESSFULLY! <<<\n")
gdb.execute("quit")
