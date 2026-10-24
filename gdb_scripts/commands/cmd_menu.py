"""
gdb_scripts/commands/cmd_menu.py
---------------------------------
Command Palette (menu / alias h):
Slash-style interactive command selector for HM-Debugger v2.
Allows users to navigate via ↑/↓ and Enter to run any HM analysis command.
"""

from typing import List, Optional
from gdb_scripts.ui.picker import run_picker, PickerItem
from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


COMMAND_CATALOG = [
    PickerItem(
        label="/hs",
        value="hs",
        description="Step Pipeline Tour: Walk sequentially through 7 HM C++ stages"
    ),
    PickerItem(
        label="/hs intra",
        value="hs intra",
        description="Intra Deep Tour: Step sequentially inside xCheckRDCostIntra (8 stages)"
    ),
    PickerItem(
        label="/hn",
        value="hn",
        description="Step RDO Candidate: Jump to next trial & render Auto-Diff table"
    ),
    PickerItem(
        label="/hv",
        value="hv",
        description="Variable Inspector: Interactive drill-down variable browser"
    ),
    PickerItem(
        label="/hw",
        value="hw",
        description="Where Am I: Show call hierarchy breadcrumbs & 7-stage roadmap"
    ),
    PickerItem(
        label="/hi",
        value="hi",
        description="Inspect Context: Snapshot of active variables at current stage"
    ),
    PickerItem(
        label="/hd",
        value="hd",
        description="Diff RDO Metrics: Detailed comparison (Cost, Bits, Distortion)"
    ),
    PickerItem(
        label="/hg",
        value="hg",
        description="View CTU Grid: 16x16 SCU raster map of Depth and PartMode"
    ),
    PickerItem(
        label="/ha",
        value="ha depth",
        description="CU Arrays: Dump internal 1D depth/intra/cbf buffers"
    ),
    PickerItem(
        label="/hp",
        value="hp orig 8",
        description="Pixel Matrix: Display 2D Luma pixel values (pred/orig/resi)"
    ),
    PickerItem(
        label="/hc",
        value="hc",
        description="Encoder Config: View active pilot 64x64 encoder settings"
    ),
    PickerItem(
        label="/ht",
        value="ht",
        description="Trace Breakpoints: Enable dynamic breakpoints (intra/inter/off)"
    ),
    PickerItem(
        label="/hm-status",
        value="hm-status",
        description="Session Status: View target CTU/POC & candidate trial count"
    )
]


class CmdCommandPalette(gdb.Command if gdb else object):
    """Open interactive Command Palette to select and execute any HM command.
    Syntax: menu (or alias: h)
    Use ↑/↓ arrows to navigate, Enter or Tab to run, and Esc to exit.
    """

    def __init__(self, name: str = "menu"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        if hasattr(self, "dont_repeat"):
            self.dont_repeat()

        selected = run_picker(
            title="",
            items=COMMAND_CATALOG,
            default_idx=0,
            max_visible=6,
            is_interactive=from_tty
        )

        if not selected or not selected.value:
            return

        cmd = selected.value
        if not from_tty:
            print(f"{c_dim('Batch verified command palette selection:')} {c_bold(c_green(cmd))}")
            return

        print(f"{c_dim('Executing:')} {c_bold(c_green(cmd))} {c_dim('[Tip: To step forward by pressing Enter, type directly: ' + cmd + ']')}")
        try:
            if gdb:
                gdb.execute(cmd)
        except gdb.error as err:
            print(f"[HM-Menu] Error executing '{cmd}': {err}")
