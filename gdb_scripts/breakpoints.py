"""
gdb_scripts/breakpoints.py
--------------------------
Quản lý các Breakpoint chiến lược trong HM-18.0:
1. RdoTrialBreakpoint: Bắt mọi lần so sánh candidate tại entry của TEncCu::xCheckBestMode.
2. CuCommitBreakpoint: Bắt mốc chốt phương án cuối cùng tại entry của TEncCu::xCopyYuv2Pic.
"""

from typing import Optional
from gdb_scripts.core.session import InspectorSession
from gdb_scripts.adapters.tcom_data_cu import TComDataCUAdapter
from gdb_scripts.ui.colors import c_green, c_yellow, c_bold, c_cyan, c_dim
from gdb_scripts.ui.renderers import render_compact_context_panel

try:
    import gdb
except ImportError:
    gdb = None


class RdoTrialBreakpoint(gdb.Breakpoint if gdb else object):
    """
    Breakpoint tại entry của TEncCu::xCheckBestMode.
    Lọc chặt chẽ theo target CTU và target POC.
    """

    def __init__(self):
        if gdb:
            super().__init__("TEncCu::xCheckBestMode", gdb.BP_BREAKPOINT, internal=False)
            self.silent = True

    def stop(self) -> bool:
        """Được GDB tự động gọi mỗi khi chạm breakpoint."""
        if not gdb:
            return False

        session = InspectorSession.get_instance()
        if not session.is_active:
            return False

        try:
            frame = gdb.selected_frame()
            if "xCheckBestMode" not in frame.name():
                return False

            rpcTempCU = frame.read_var("rpcTempCU")
            rpcBestCU = frame.read_var("rpcBestCU")
            uiDepth = int(frame.read_var("uiDepth"))

            trial = TComDataCUAdapter(rpcTempCU)
            best = TComDataCUAdapter(rpcBestCU)

            if not trial.is_valid:
                return False

            # Bộ lọc an toàn: Chỉ dừng đúng CTU và POC mục tiêu
            if trial.ctu_rs_addr != session.target_ctu or trial.poc != session.target_poc:
                return False

            # Cập nhật cache phiên
            session.current_trial = trial
            session.current_best = best
            session.current_depth = uiDepth
            session.candidate_count += 1

            # Render khung trạng thái Compact Context Panel 4 dòng tinh gọn
            panel = render_compact_context_panel(
                stage_num=6,
                total_stages=7,
                fn_sig="TEncCu::xCheckBestMode",
                depth=uiDepth,
                abs_z=trial.abs_z_idx,
                cand_idx=session.candidate_count,
                trial=trial,
                best=best
            )
            print(panel)

            # Dừng lại để người dùng xem/gõ lệnh
            return True

        except Exception as e:
            print(f"[HM-RDO: Error in stop filter: {e}]")
            return False


class CuCommitBreakpoint(gdb.Breakpoint if gdb else object):
    """
    Breakpoint tại entry của TEncCu::xCopyYuv2Pic.
    Chỉ được gọi duy nhất 1 lần khi CU chính thức chốt phương án chiến thắng cuối cùng.
    """

    def __init__(self, stop_on_commit: bool = False):
        self.stop_on_commit = stop_on_commit
        if gdb:
            super().__init__("TEncCu::xCopyYuv2Pic", gdb.BP_BREAKPOINT, internal=False)
            self.silent = True

    def stop(self) -> bool:
        if not gdb:
            return False

        session = InspectorSession.get_instance()
        if not session.is_active:
            return False

        try:
            frame = gdb.selected_frame()
            if "xCopyYuv2Pic" not in frame.name():
                return False

            uiCUAddr = int(frame.read_var("uiCUAddr"))
            if uiCUAddr != session.target_ctu:
                return False

            uiAbsPartIdx = int(frame.read_var("uiAbsPartIdx"))
            uiDepth = int(frame.read_var("uiDepth"))

            # Đọc rpcBestCU từ frame cha (TEncCu::xCompressCU)
            caller = frame.older()
            if caller and "xCompressCU" in caller.name():
                rpcBestCU = caller.read_var("rpcBestCU")
                best = TComDataCUAdapter(rpcBestCU)
                if best.is_valid:
                    session.commit_cu_state(best)
                    is_split = (best.depth_list and best.depth_list[0] > uiDepth)
                    decision_str = "SPLIT" if is_split else "NO-SPLIT"
                    print(f"[HM-COMMIT] Final Decision: {decision_str} | Depth: {uiDepth} | AbsZ: {uiAbsPartIdx} | Cost: {best.total_cost:,.2f}")

            return self.stop_on_commit

        except Exception as e:
            print(f"[HM-COMMIT: Error in commit filter: {e}]")
            return False
