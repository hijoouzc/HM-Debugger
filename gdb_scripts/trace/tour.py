"""
gdb_scripts/trace/tour.py
--------------------------
Bộ điều phối Pipeline Tour (hm-tour / alias hs) và Intra Deep Micro-Tour:
- Macro Tour: Dẫn dắt người dùng tuần tự qua 7 mốc vĩ mô chuẩn của HM-18.0.
- Intra Deep Micro-Tour (hs intra): Duyệt tuần tự 8 bước vi mô sâu bên trong TEncCu::xCheckRDCostIntra().
Nhấn ENTER liên tục để tiếp tục di chuyển giữa các bước.
"""

from typing import List, Dict, Any, Optional
from gdb_scripts.ui.renderers import render_stage_banner, render_menu
from gdb_scripts.core.context import inspect_current_context
from gdb_scripts.core.session import InspectorSession
from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


HM_STAGES = [
    {
        "id": 1,
        "name": "CTU Init",
        "fn": "TEncCu::compressCtu",
        "desc": "Initialize CTU buffer, clear m_ppcBestCU and m_ppcTempCU",
        "condition": "pCtu->m_ctuRsAddr == {ctu}",
        "breadcrumb": "TEncSlice::compressSlice > TEncCu::compressCtu"
    },
    {
        "id": 2,
        "name": "Quadtree Recursion",
        "fn": "TEncCu::xCompressCU",
        "desc": "Recursively test CU partition or modes at current Quadtree node",
        "condition": "rpcBestCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "TEncCu::compressCtu > TEncCu::xCompressCU"
    },
    {
        "id": 3,
        "name": "Intra 2Nx2N Trial",
        "fn": "TEncCu::xCheckRDCostIntra",
        "desc": "Test SIZE_2Nx2N partition for Intra prediction modes",
        "condition": "rpcTempCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCompressCU > TEncCu::xCheckRDCostIntra"
    },
    {
        "id": 4,
        "name": "35 Intra Search",
        "fn": "TEncSearch::estIntraPredLumaQT",
        "desc": "Evaluate MPM, angular directions, build CandCostList",
        "condition": "pcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > TEncSearch::estIntraPredLumaQT"
    },
    {
        "id": 5,
        "name": "DCT & Quantization",
        "fn": "TComTrQuant::transformNxN",
        "desc": "Perform forward DCT/DST transform and quantization for TU",
        "condition": "",
        "breadcrumb": "estIntraPredLumaQT > xRecurIntraCodingLumaQT > transformNxN"
    },
    {
        "id": 6,
        "name": "RDO Best Decision",
        "fn": "TEncCu::xCheckBestMode",
        "desc": "Compare RD cost between rpcTempCU and rpcBestCU",
        "condition": "rpcTempCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > TEncCu::xCheckBestMode"
    },
    {
        "id": 7,
        "name": "CU Picture Commit",
        "fn": "TEncCu::xCopyYuv2Pic",
        "desc": "Copy winner CU reconstructed samples to Picture buffer",
        "condition": "",
        "breadcrumb": "compressCtu > TEncCu::xCopyYuv2Pic"
    }
]


HM_INTRA_STAGES = [
    {
        "id": 1,
        "name": "CU Intra Setup",
        "fn": "TEncCu::xCheckRDCostIntra",
        "desc": "Initialize candidate: setPartSizeSubParts(eSize) & setPredModeSubParts(MODE_INTRA)",
        "condition": "rpcTempCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "TEncCu::compressCtu > xCompressCU > xCheckRDCostIntra"
    },
    {
        "id": 2,
        "name": "Angular Prediction",
        "fn": "TComPrediction::predIntraAng",
        "desc": "Generate directional Intra sample prediction against reconstructed boundary pixels",
        "condition": "rTu.mpcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > estIntraPredLumaQT > predIntraAng"
    },
    {
        "id": 3,
        "name": "DCT & Quantization",
        "fn": "TComTrQuant::transformNxN",
        "desc": "Forward 2D DCT/DST transform & RDOQ quantization on prediction residual",
        "condition": "rTu.mpcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > estIntraPredLumaQT > xRecurIntraCodingLumaQT > transformNxN"
    },
    {
        "id": 4,
        "name": "InvTransform & Reco",
        "fn": "TComTrQuant::invTransformNxN",
        "desc": "Inverse quantization & IDCT/IDST to reconstruct residual samples & calculate distortion",
        "condition": "rTu.mpcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > estIntraPredLumaQT > xRecurIntraCodingLumaQT > invTransformNxN"
    },
    {
        "id": 5,
        "name": "Chroma Intra Search",
        "fn": "TEncSearch::estIntraPredChromaQT",
        "desc": "Evaluate Chroma intra prediction modes (DM, Planar, Angular) & RQT distortion",
        "condition": "pcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > estIntraPredChromaQT"
    },
    {
        "id": 6,
        "name": "CABAC Entropy Coder",
        "fn": "TEncEntropy::xEncodeTransform",
        "desc": "CABAC bitstream modeling: split flags, CBF, coded QP & transform coefficients",
        "condition": "rTu.mpcCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > encodeCoeff > xEncodeTransform"
    },
    {
        "id": 7,
        "name": "RD Cost Calculation",
        "fn": "TEncCu.cpp:1748",
        "desc": "Finalize candidate metrics: TotalBits, TotalBins, TotalDistortion & Cost = D + lambda * R",
        "condition": "rpcTempCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > calcRdCost(Bits, Distortion)"
    },
    {
        "id": 8,
        "name": "RDO Best Decision",
        "fn": "TEncCu::xCheckBestMode",
        "desc": "Compare candidate Cost vs current Best CU; commit to Best if Cost is lower",
        "condition": "rpcTempCU->m_ctuRsAddr == {ctu}",
        "breadcrumb": "xCheckRDCostIntra > xCheckBestMode"
    }
]


class PipelineTour:
    """Bộ điều phối hành trình duyệt từng hàm con (Macro & Intra Micro Tour)."""
    _instance: Optional["PipelineTour"] = None

    def __init__(self):
        self.current_mode: str = "macro"
        self.current_stage_idx: int = 0
        self.temp_bp: Optional[Any] = None

    @classmethod
    def get_instance(cls) -> "PipelineTour":
        if cls._instance is None:
            cls._instance = PipelineTour()
        return cls._instance

    def reset(self):
        self.current_stage_idx = 0
        if self.temp_bp:
            try:
                self.temp_bp.delete()
            except Exception:
                pass
            self.temp_bp = None

    def switch_mode(self, mode: str):
        mode = mode.lower().strip()
        target_mode = "intra" if mode in ("intra", "micro", "micro-intra") else "macro"
        if target_mode != self.current_mode:
            self.reset()
            self.current_mode = target_mode
            if target_mode == "intra":
                print(f"[HM-Tour] Switched to {c_bold(c_yellow('Intra Micro-Tour'))} (8 stages inside xCheckRDCostIntra).")
            else:
                print(f"[HM-Tour] Switched to {c_bold(c_cyan('Macro Pipeline Tour'))} (7 core CTU stages).")

    def show_menu(self, mode: Optional[str] = None):
        """In danh sách các mốc của tour."""
        show_intra = (mode in ("intra", "micro", "micro-intra")) if mode else (self.current_mode == "intra")
        if show_intra:
            print(render_menu(
                HM_INTRA_STAGES,
                title="HM-18.0 INTRA MICRO-TOUR: TEncCu::xCheckRDCostIntra()",
                footer="  Run: hs intra (step intra tour) | hs macro (switch macro) | hm-start"
            ))
        else:
            print(render_menu(
                HM_STAGES,
                title="HM-18.0 CTU ENCODING PIPELINE (7 CORE STAGES)",
                footer="  Run: hs (step tour) | hs intra (deep intra tour) | hm-trace <module>"
            ))

    def _execute_stage(self, stage_idx: int, force_run: bool = False):
        """Thực thi tới mốc stage_idx (0-based) và in giao diện context."""
        if gdb is None:
            print("[HM-Tour] GDB is not available.")
            return

        session = InspectorSession.get_instance()
        target_ctu = session.target_ctu

        active_stages = HM_INTRA_STAGES if self.current_mode == "intra" else HM_STAGES
        total_stages = len(active_stages)
        stage_info = active_stages[stage_idx]

        # Xóa breakpoint tạm thời trước đó nếu có
        if self.temp_bp:
            try:
                self.temp_bp.delete()
            except Exception:
                pass
            self.temp_bp = None

        fn_target = stage_info["fn"]
        cond = stage_info["condition"].format(ctu=target_ctu) if stage_info.get("condition") else ""

        try:
            bp_spec = f"{fn_target}"
            if cond:
                bp_spec += f" if {cond}"

            self.temp_bp = gdb.Breakpoint(bp_spec, temporary=True, internal=True)
            self.temp_bp.silent = True

            inf = gdb.selected_inferior()
            if force_run or not inf or inf.pid == 0:
                # Trích xuất arguments hiện tại để chạy kèm chuyển hướng output, tránh in tràn bảng config của HM
                run_cmd = "run"
                try:
                    out = gdb.execute("show args", to_string=True).strip()
                    if 'is "' in out and out.endswith('".'):
                        prog_args = out.split('is "', 1)[1][:-2]
                        run_cmd = f"run {prog_args} &> /dev/null"
                except Exception:
                    run_cmd = "run"

                gdb.execute("set confirm off")
                gdb.execute(run_cmd)
                gdb.execute("set confirm on")
            else:
                gdb.execute("continue")

            inf = gdb.selected_inferior()
            if not inf or inf.pid == 0:
                print("\n[HM-Tour] Program finished execution.")
                return

            banner = render_stage_banner(
                stage_idx + 1,
                total_stages,
                stage_info["name"],
                stage_info["fn"],
                stage_info["desc"],
                breadcrumb=stage_info.get("breadcrumb", "")
            )
            print(banner)

            print(inspect_current_context())
            print()

            # Nếu là mốc RDO Best Decision, in thêm bảng Auto-Diff so sánh
            if "xCheckBestMode" in stage_info["fn"]:
                try:
                    from gdb_scripts.core.evaluator import RDOEvaluator
                    from gdb_scripts.ui.renderers import render_diff_table
                    best, temp = RDOEvaluator.get_instance().evaluate_current_frame()
                    if best and temp and (best.is_valid or temp.is_valid):
                        print(render_diff_table(best, temp))
                        print()
                except Exception:
                    pass

            self.current_stage_idx = (stage_idx + 1) % total_stages

        except gdb.error as err:
            if "The program is not being run" in str(err) or "exited" in str(err):
                print("\n[HM-Tour] Program finished execution.")
            else:
                print(f"[HM-Tour] Execution note: {err}")

    def step_next(self, mode: Optional[str] = None):
        """Tiến tới mốc tiếp theo trong danh sách mốc hiện tại."""
        if mode:
            mode = mode.lower().strip()
            if mode in ("intra", "micro", "micro-intra") and self.current_mode != "intra":
                self.switch_mode("intra")
            elif mode in ("macro", "ctu", "main") and self.current_mode != "macro":
                self.switch_mode("macro")

        self._execute_stage(self.current_stage_idx, force_run=False)

    def goto_stage(self, target_1based: int, mode: Optional[str] = None):
        """Nhảy trực tiếp tới mốc mong muốn (1-based index).
        Nếu mốc mong muốn <= mốc hiện tại, tự động re-run để tua ngược trạng thái bộ nhớ.
        """
        if mode:
            mode = mode.lower().strip()
            if mode in ("intra", "micro", "micro-intra") and self.current_mode != "intra":
                self.switch_mode("intra")
            elif mode in ("macro", "ctu", "main") and self.current_mode != "macro":
                self.switch_mode("macro")

        active_stages = HM_INTRA_STAGES if self.current_mode == "intra" else HM_STAGES
        total_stages = len(active_stages)

        if target_1based < 1 or target_1based > total_stages:
            print(f"[HM-Tour] Mốc không hợp lệ: {target_1based}. Giá trị hợp lệ từ 1 đến {total_stages}.")
            return

        target_idx = target_1based - 1
        inf = gdb.selected_inferior() if gdb else None
        need_rerun = bool(inf and inf.pid != 0 and target_idx < self.current_stage_idx)

        if need_rerun:
            print(f"[HM-Tour] Tua ngược tiến trình về mốc [{target_1based}/{total_stages}]...")

        self._execute_stage(target_idx, force_run=need_rerun)

    def step_back(self):
        """Quay lại mốc thuật toán trước đó."""
        active_stages = HM_INTRA_STAGES if self.current_mode == "intra" else HM_STAGES
        total_stages = len(active_stages)
        # self.current_stage_idx lưu mốc tiếp theo sẽ chạy
        cur_on_screen = self.current_stage_idx if self.current_stage_idx > 0 else 1
        prev_stage = cur_on_screen - 1 if cur_on_screen > 1 else 1
        self.goto_stage(prev_stage)
