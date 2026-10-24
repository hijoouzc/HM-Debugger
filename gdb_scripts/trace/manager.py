"""
gdb_scripts/trace/manager.py
-----------------------------
Quản lý dynamic breakpoints theo module (Intra, Inter, Transform, Split).
Hỗ trợ tự động đặt điều kiện lọc đúng target CTU và tự hoàn thành tham số Tab.
"""

from typing import Dict, List, Optional
from gdb_scripts.core.session import InspectorSession
from gdb_scripts.ui.colors import c_green, c_yellow, c_red, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


class DynamicTraceBreakpoint(gdb.Breakpoint if gdb else object):
    """Breakpoint chuyên biệt cho dynamic trace, tự động hiển thị ngữ cảnh khi dừng."""
    def __init__(self, spec: str, module_name: str, desc: str):
        if gdb:
            super().__init__(spec, gdb.BP_BREAKPOINT, internal=False)
            self.silent = True
        self.module_name = module_name
        self.desc = desc

    def stop(self) -> bool:
        try:
            from gdb_scripts.core.context import inspect_current_context
            bar_len = max(10, 72 - len(self.module_name) - len(self.desc) - 14)
            print(f"\n{c_cyan('┌─ ')}{c_bold(c_yellow(f'[TRACE: {self.module_name.upper()}] {self.desc}'))} {c_cyan('─' * bar_len + '┐')}")
            print(inspect_current_context())
            print(f"  {c_dim('[Hint: Type \"c\" to continue | \"hi\" to inspect | \"hw\" for map | \"hp orig 8\" for pixels]')}")
            print(c_cyan("└" + "─" * 74 + "┘\n"))
        except Exception as e:
            pass
        return True


class TraceManager:
    """Quản lý các điểm dừng chuyên sâu theo module."""
    _instance: Optional["TraceManager"] = None

    MODULES = {
        "intra": {
            "fn": "TEncSearch::estIntraPredLumaQT",
            "cond": "pcCU->m_ctuRsAddr == {ctu}",
            "desc": "Search 35 Intra Luma modes & evaluate CandCostList"
        },
        "inter": {
            "fn": "TEncSearch::predInterSearch",
            "cond": "pcCU->m_ctuRsAddr == {ctu}",
            "desc": "Motion Estimation (ME) & Motion Vector (MV) search"
        },
        "merge": {
            "fn": "TEncCu::xCheckRDCostMerge2Nx2N",
            "cond": "rpcTempCU->m_ctuRsAddr == {ctu}",
            "desc": "Evaluate Skip / Merge 2Nx2N candidates"
        },
        "transform": {
            "fn": "TComTrQuant::transformNxN",
            "cond": "",
            "desc": "TU Forward DCT/DST transform"
        },
        "quant": {
            "fn": "TComTrQuant::xQuant",
            "cond": "",
            "desc": "RDOQ rate-distortion optimized quantization"
        },
        "split": {
            "fn": "TEncCu::xCompressCU",
            "cond": "rpcBestCU->m_ctuRsAddr == {ctu} && uiDepth >= 1",
            "desc": "Recursive Quadtree CU split (uiDepth 1, 2, 3)"
        }
    }

    def __init__(self):
        self.active_bps: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> "TraceManager":
        if cls._instance is None:
            cls._instance = TraceManager()
        return cls._instance

    def enable_module(self, module_name: str) -> bool:
        """Bật trace cho một module cụ thể."""
        if gdb is None:
            return False

        module_name = module_name.lower().strip()
        if module_name not in self.MODULES:
            print(f"[HM-Trace] Module '{module_name}' not found. Valid modules: {', '.join(self.MODULES.keys())}, all, off")
            return False

        # Nếu đã có, xóa cũ trước
        self.disable_module(module_name)

        session = InspectorSession.get_instance()
        target_ctu = session.target_ctu

        mod_cfg = self.MODULES[module_name]
        spec = mod_cfg["fn"]
        if mod_cfg["cond"]:
            spec += " if " + mod_cfg["cond"].format(ctu=target_ctu)

        try:
            bp = DynamicTraceBreakpoint(spec, module_name, mod_cfg["desc"])
            self.active_bps[module_name] = bp
            print(f"  {c_green('✔ Trace enabled:')} {c_bold(module_name.upper())} ({mod_cfg['desc']})")
            return True
        except gdb.error as err:
            print(f"  {c_red('✖ Error setting breakpoint:')} {err}")
            return False

    def disable_module(self, module_name: str):
        """Tắt trace cho một module."""
        module_name = module_name.lower().strip()
        if module_name in self.active_bps:
            try:
                self.active_bps[module_name].delete()
            except Exception:
                pass
            del self.active_bps[module_name]
            print(f"  {c_yellow('○ Trace disabled:')} {module_name.upper()}")

    def disable_all(self):
        """Tắt tất cả các trace breakpoint."""
        for mod in list(self.active_bps.keys()):
            self.disable_module(mod)
        print(f"  {c_dim('Cleared all dynamic trace breakpoints.')}")
