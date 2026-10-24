"""
gdb_scripts/commands/__init__.py
---------------------------------
Đăng ký toàn bộ danh mục lệnh chính và alias 2 ký tự vào GDB.
"""

from .cmd_start import CmdHmStart
from .cmd_tour import CmdHmTour, CmdHmMenu
from .cmd_menu import CmdCommandPalette
from .cmd_var_picker import CmdHmVar
from .cmd_control import CmdHmInit, CmdHmNextRd, CmdHmStatus
from .cmd_inspect import CmdHmInspect, CmdHmDiffCu, CmdHmWhere
from .cmd_view import CmdHmPrintGrid, CmdHmPrintArray, CmdHmPrintPixels
from .cmd_trace import CmdHmTrace
from .cmd_help import CmdHmHelp
from .cmd_test import CmdHmTest
from .cmd_config import CmdHmConfig, CmdHc

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmPrefix(gdb.Command if gdb else object):
    """Lệnh tiền tố hm cho phép gõ: hm next, hm tour, hm inspect, hm grid, hm test..."""
    def __init__(self):
        if gdb:
            super().__init__("hm", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND, prefix=True)


def register_all_commands():
    """Đăng ký toàn bộ các command và shortcut alias vào GDB."""
    # 0. Lệnh tiền tố hm
    CmdHmPrefix()

    # 1. Khởi động 1 bước
    CmdHmStart()

    # 2. Tour tuần tự qua từng hàm
    CmdHmTour("hm-tour")
    CmdHmTour("hs")       # Shortcut alias
    CmdHmTour("hm tour")  # Subcommand alias
    CmdHmMenu()

    # 3. Điều khiển candidate RDO
    CmdHmInit()
    CmdHmNextRd("hm-next-rd")
    CmdHmNextRd("hn")       # Shortcut alias
    CmdHmNextRd("hm next")  # Subcommand alias
    CmdHmStatus()

    # 4. Soi biến và so sánh
    CmdHmInspect("hm-inspect")
    CmdHmInspect("hi")          # Shortcut alias
    CmdHmInspect("hm inspect")  # Subcommand alias
    CmdHmVar("hm-var")
    CmdHmVar("hv")              # Shortcut alias
    CmdHmVar("hm var")          # Subcommand alias
    CmdHmDiffCu("hm-diff-cu")
    CmdHmDiffCu("hd")           # Shortcut alias
    CmdHmDiffCu("hm diff")      # Subcommand alias
    CmdHmWhere("hm-where")
    CmdHmWhere("hw")            # Shortcut alias
    CmdHmWhere("hm where")      # Subcommand alias

    # 4.1 Command Palette tương tác
    CmdCommandPalette("menu")
    CmdCommandPalette("h")

    # 5. Xem lưới và mảng
    CmdHmPrintGrid("hm-print-grid")
    CmdHmPrintGrid("hg")        # Shortcut alias
    CmdHmPrintGrid("hm grid")   # Subcommand alias
    CmdHmPrintArray("hm-print-array")
    CmdHmPrintArray("ha")       # Shortcut alias
    CmdHmPrintPixels("hm-print-pixels")
    CmdHmPrintPixels("hp")      # Shortcut alias

    # 6. Quản lý trace
    CmdHmTrace("hm-trace")
    CmdHmTrace("ht")            # Shortcut alias

    # 7. Trợ giúp & Kiểm thử
    CmdHmHelp()
    CmdHmConfig()
    CmdHc()
    CmdHmTest("hm-test")
    CmdHmTest("test")           # Alias cho test
    CmdHmTest("hm test")        # Subcommand cho hm test
