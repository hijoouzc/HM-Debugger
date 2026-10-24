"""
gdb_scripts/commands/cmd_help.py
---------------------------------
Lệnh hm-help: Bảng tra cứu phím tắt nhanh và hướng dẫn sử dụng trực quan.
"""

from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmHelp(gdb.Command if gdb else object):
    """Hiển thị bảng tra cứu nhanh các lệnh của HM-Debugger v2.
    Cú pháp: hm-help
    """

    def __init__(self):
        if gdb:
            super().__init__("hm-help", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        lines = [
            c_cyan("╔" + "═" * 76 + "╗"),
            c_cyan("║") + c_bold(c_yellow("         HM-GDB-INSPECTOR V2: QUICK REFERENCE & SHORTCUT GUIDE        ")).center(85) + c_cyan("║"),
            c_cyan("╠" + "═" * 76 + "╣"),
            f"  {c_bold(c_green('hm-start'))} [ctu] [poc]    : 1-step init session, load config & set target CTU/POC",
            f"  {c_bold(c_green('menu'))}     (or {c_bold('h')})            : COMMAND PALETTE: Interactive slash-style arrow picker (↑/↓)",
            f"  {c_bold(c_green('hv'))}       (or {c_bold('hm-var')})       : VARIABLE INSPECTOR: Interactive drill-down variable browser",
            c_dim("  " + "─" * 74),
            f"  {c_bold(c_green('hs'))}  (or {c_bold('hm-tour')})       : STEP PIPELINE: Walk sequentially through 7 HM C++ stages",
            f"        hs intra             : Deep Micro-Tour: Step 8 sub-stages inside xCheckRDCostIntra",
            f"        hs back (or hs b)    : Rewind execution back to previous sub-stage",
            f"        hs <1..8>            : Jump directly to stage N (e.g. hs 2)",
            f"                             (Press {c_yellow('ENTER')} repeatedly to continue through stages)",
            f"  {c_bold(c_green('hn'))}  (or {c_bold('hm-next-rd')})    : STEP RDO: Jump to next RDO trial candidate",
            f"                             (Automatically renders Auto-Diff Best vs Temp table)",
            c_dim("  " + "─" * 74),
            f"  {c_bold(c_green('hi'))}  (or {c_bold('hm-inspect')})    : INSPECT: Context-aware inspection of active variables",
            f"        hi <var_name>        : Deep unpack struct/class members recursively",
            f"  {c_bold(c_green('hw'))}  (or {c_bold('hm-where')})      : WHERE AM I: Display call hierarchy breadcrumb & 7-stage map",
            f"  {c_bold(c_green('hd'))}  (or {c_bold('hm-diff-cu')})    : Render detailed RDO metric diff (Cost, Bits, Distortion)",
            f"  {c_bold(c_green('hg'))}  (or {c_bold('hm-grid')})       : VIEW CTU GRID: 16x16 SCU raster map of Depth/Mode",
            f"  {c_bold(c_green('ha'))} <depth|intra|cbf>   : Print 1D internal CU partition arrays",
            f"  {c_bold(c_green('hp'))} [pred|orig|resi]    : Print 2D Luma pixel matrix",
            c_dim("  " + "─" * 74),
            f"  {c_bold(c_green('ht'))} <intra|inter|off>   : Enable/disable dynamic trace breakpoints (TAB completion)",
            f"  {c_bold(c_green('hc'))}  (or {c_bold('hm-config')})     : Display encoder configuration summary (Pilot 64x64)",
            f"  {c_bold(c_green('hm-menu'))}                  : Display HM-18.0 7-stage pipeline reference menu",
            f"  {c_bold(c_green('hm-status'))}                : Display active debugging session status",
            c_cyan("╚" + "═" * 76 + "╝"),
        ]
        print("\n".join(lines))
