"""
gdb_scripts/commands/cmd_tour.py
---------------------------------
Lệnh hm-tour (alias hs) và hm-menu:
Điều hướng tuần tự qua 7 mốc hàm con chuẩn trong HM-18.0.
"""

from gdb_scripts.trace.tour import PipelineTour

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmTour(gdb.Command if gdb else object):
    """Tiến tới hoặc lùi lại mốc thuật toán trong HM-18.0 (Macro Tour hoặc Intra Micro-Tour).
    Cú pháp:
      hs (hoặc hm-tour)             : Tiến tới mốc tiếp theo trong tour hiện tại
      hs back (hoặc hs b)           : Quay lại mốc thuật toán trước đó (tự động tua ngược)
      hs <số> (ví dụ: hs 2)         : Nhảy trực tiếp tới mốc chỉ định (1..8)
      hs intra [số]                 : Chuyển sang Intra Deep Micro-Tour (8 bước trong xCheckRDCostIntra)
      hs macro [số]                 : Quay lại Macro Pipeline Tour (7 mốc CTU)
      hs reset                      : Đặt lại tour về mốc đầu tiên [1]
    Sau khi gõ hs lần đầu, chỉ việc nhấn ENTER liên tục để duyệt tuần tự.
    """

    SUBCOMMANDS = ["intra", "macro", "back", "reset", "menu"]

    def __init__(self, name: str = "hm-tour"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def complete(self, text: str, word: str) -> list:
        return [sub for sub in self.SUBCOMMANDS if sub.startswith(word.lower())]

    def invoke(self, arg: str, from_tty: bool):
        arg_clean = arg.strip().lower()
        tokens = arg_clean.split()
        if not tokens:
            PipelineTour.get_instance().step_next()
            return

        mode = None
        target_num = None
        is_back = False
        is_reset = False
        is_menu = False

        for t in tokens:
            if t in ("intra", "micro", "micro-intra"):
                mode = "intra"
            elif t in ("macro", "ctu", "main"):
                mode = "macro"
            elif t in ("back", "prev", "b"):
                is_back = True
            elif t == "reset":
                is_reset = True
            elif t == "menu":
                is_menu = True
            elif t.isdigit():
                target_num = int(t)

        tour = PipelineTour.get_instance()
        if is_menu:
            tour.show_menu(mode=mode)
        elif is_reset:
            tour.reset()
            if mode:
                tour.switch_mode(mode)
            print("[HM-Tour] Reset tour back to stage [1].")
        elif is_back:
            if mode:
                tour.switch_mode(mode)
            tour.step_back()
        elif target_num is not None:
            tour.goto_stage(target_num, mode=mode)
        else:
            tour.step_next(mode=mode)


class CmdHmMenu(gdb.Command if gdb else object):
    """Hiển thị menu danh sách các mốc thuật toán của HM-18.0.
    Cú pháp:
      hm-menu       : Xem 7 mốc Macro CTU Pipeline
      hm-menu intra : Xem 8 mốc Intra Deep Micro-Tour (xCheckRDCostIntra)
    """

    SUBCOMMANDS = ["intra", "macro"]

    def __init__(self):
        if gdb:
            super().__init__("hm-menu", gdb.COMMAND_USER)

    def complete(self, text: str, word: str) -> list:
        return [sub for sub in self.SUBCOMMANDS if sub.startswith(word.lower())]

    def invoke(self, arg: str, from_tty: bool):
        arg_clean = arg.strip().lower()
        mode = "intra" if arg_clean in ("intra", "micro") else "macro" if arg_clean == "macro" else None
        PipelineTour.get_instance().show_menu(mode=mode)
