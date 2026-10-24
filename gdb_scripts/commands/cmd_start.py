"""
gdb_scripts/commands/cmd_start.py
----------------------------------
Lệnh hm-start: Khởi động 1 bước toàn bộ môi trường gỡ lỗi CTU 64x64.
"""

from gdb_scripts.core.session import InspectorSession
from gdb_scripts.breakpoints import RdoTrialBreakpoint, CuCommitBreakpoint
from gdb_scripts.trace.tour import PipelineTour
from gdb_scripts.ui.renderers import render_startup_banner

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmStart(gdb.Command if gdb else object):
    """Khởi động toàn bộ môi trường gỡ lỗi chỉ với 1 lệnh duy nhất.
    Cú pháp: hm-start [target_ctu=0] [target_poc=0]
    """

    def __init__(self):
        if gdb:
            super().__init__("hm-start", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        target_ctu = int(args[0]) if len(args) > 0 else 0
        target_poc = int(args[1]) if len(args) > 1 else 0

        # Khởi tạo phiên
        session = InspectorSession.get_instance()
        session.reset(target_ctu=target_ctu, target_poc=target_poc)
        PipelineTour.get_instance().reset()

        # Đăng ký các breakpoint chiến lược RDO và Commit
        if not hasattr(session, "bp_trial") or session.bp_trial is None:
            session.bp_trial = RdoTrialBreakpoint()
            session.bp_commit = CuCommitBreakpoint(stop_on_commit=True)

        print(render_startup_banner(target_ctu=target_ctu, target_poc=target_poc))
