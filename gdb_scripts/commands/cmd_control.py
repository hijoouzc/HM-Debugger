"""
gdb_scripts/commands/cmd_control.py
------------------------------------
Lệnh điều khiển phiên và duyệt RDO candidate:
- hm-init
- hm-next-rd (alias: hn) với Auto-Diff
- hm-status
"""

from gdb_scripts.core.session import InspectorSession
from gdb_scripts.breakpoints import RdoTrialBreakpoint, CuCommitBreakpoint
from gdb_scripts.ui.renderers import render_diff_table
from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmInit(gdb.Command if gdb else object):
    """Khởi tạo phiên quan sát cho một CTU và POC cụ thể.
    Cú pháp: hm-init [target_ctu=0] [target_poc=0]
    """

    def __init__(self):
        if gdb:
            super().__init__("hm-init", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        target_ctu = int(args[0]) if len(args) > 0 else 0
        target_poc = int(args[1]) if len(args) > 1 else 0

        session = InspectorSession.get_instance()
        session.reset(target_ctu=target_ctu, target_poc=target_poc)

        if not hasattr(session, "bp_trial") or session.bp_trial is None:
            session.bp_trial = RdoTrialBreakpoint()
            session.bp_commit = CuCommitBreakpoint(stop_on_commit=True)

        print(f"[HM-Debugger] Initialized: Target CTU: {target_ctu} | Target POC: {target_poc}")
        print("  Type 'run' (or 'continue') to start. Use 'hn' to step through candidates.")


class CmdHmNextRd(gdb.Command if gdb else object):
    """Continue execution to next RDO candidate and automatically render comparison table.
    Syntax: hm-next-rd (or alias: hn)
    After typing hn, press ENTER repeatedly to step smoothly.
    """

    def __init__(self, name: str = "hm-next-rd"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        session = InspectorSession.get_instance()
        if not session.is_active:
            print("[HM-Debugger] Please run 'hm-start' first!")
            return

        try:
            inf = gdb.selected_inferior()
            if not inf or inf.pid == 0:
                gdb.execute("run")
            else:
                gdb.execute("continue")

            # Khi dừng tại xCheckBestMode, tự động in bảng Auto-Diff
            if session.current_trial and session.current_best:
                diff_output = render_diff_table(session.current_best, session.current_trial)
                print(f"\n{c_cyan('---')} Candidate #{session.candidate_count} {c_cyan('---')}")
                print(diff_output)
                print(c_dim("  [Press ENTER to step to next candidate]"))

        except gdb.error as err:
            if "The program is not being run" in str(err) or "exited" in str(err):
                print(f"\n{c_yellow('[HM-Debugger] Encoder finished frame or target CTU not found.')}")
            else:
                print(f"[HM-Debugger] Execution note: {err}")


class CmdHmStatus(gdb.Command if gdb else object):
    """Display active debugging session summary.
    Syntax: hm-status
    """

    def __init__(self):
        if gdb:
            super().__init__("hm-status", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        session = InspectorSession.get_instance()
        if not session.is_active:
            print("[HM-Debugger] Session is not active. Type 'hm-start' first!")
            return

        lines = [
            f"\n{c_cyan('===')} {c_bold('HM-GDB-INSPECTOR SESSION STATUS')} {c_cyan('===')}",
            f"  Target CTU (m_ctuRsAddr)      : {session.target_ctu}",
            f"  Target POC (m_iPOC)           : {session.target_poc}",
            f"  Candidate Count               : {session.candidate_count}",
            f"  uiDepth                       : {session.current_depth}",
        ]
        if session.current_best and session.current_best.is_valid:
            c_str = "INF" if session.current_best.total_cost >= 1e300 else f"{session.current_best.total_cost:,.2f}"
            lines.append(f"  rpcBestCU                     : m_dTotalCost={c_str} | Part={session.current_best.part_size_str}")
        if session.current_trial and session.current_trial.is_valid:
            c_str = "INF" if session.current_trial.total_cost >= 1e300 else f"{session.current_trial.total_cost:,.2f}"
            lines.append(f"  rpcTempCU                     : m_dTotalCost={c_str} | Part={session.current_trial.part_size_str}")
        lines.append(c_cyan("=" * 44) + "\n")
        print("\n".join(lines))
