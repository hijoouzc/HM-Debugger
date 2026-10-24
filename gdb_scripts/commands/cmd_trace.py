"""
gdb_scripts/commands/cmd_trace.py
----------------------------------
Lệnh hm-trace (alias ht):
Quản lý breakpoint theo module với Tab-completion tự động.
"""

from gdb_scripts.trace.manager import TraceManager

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmTrace(gdb.Command if gdb else object):
    """Bật/tắt trace điểm dừng thông minh theo module.
    Cú pháp: hm-trace <intra|inter|transform|split|all|off> (hoặc alias: ht)
    Hỗ trợ nhấn phím TAB để tự động gợi ý module.
    """

    SUBCOMMANDS = ["intra", "inter", "merge", "quant", "transform", "split", "all", "off"]

    def __init__(self, name: str = "hm-trace"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def complete(self, text: str, word: str) -> list:
        """Gợi ý Tab-completion tự động của GDB."""
        return [sub for sub in self.SUBCOMMANDS if sub.startswith(word.lower())]

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        if not args:
            print("Syntax: ht <intra|inter|transform|split|all|off>")
            return

        cmd = args[0].lower()
        mgr = TraceManager.get_instance()

        if cmd == "off":
            mgr.disable_all()
        elif cmd == "all":
            for mod in ["intra", "inter", "transform", "split"]:
                mgr.enable_module(mod)
        elif cmd in mgr.MODULES:
            mgr.enable_module(cmd)
        else:
            print(f"Invalid module '{cmd}'. Choose from: {', '.join(self.SUBCOMMANDS)}")
