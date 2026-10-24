"""
gdb_scripts/commands/cmd_inspect.py
------------------------------------
Lệnh hm-inspect (alias hi) và hm-diff-cu (alias hd):
Soi biến ngữ cảnh thông minh, duyệt object tổng quát và in bảng so sánh RDO.
"""

from gdb_scripts.core.session import InspectorSession
from gdb_scripts.core.inspector import GenericObjectInspector
from gdb_scripts.core.context import inspect_current_context
from gdb_scripts.ui.renderers import render_diff_table
from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmInspect(gdb.Command if gdb else object):
    """Soi biến thông minh theo ngữ cảnh hoặc duyệt bung cấu trúc struct/class C++.
    Cú pháp:
      1. hi                      : Tự nhận diện hàm hiện tại và in biến cốt lõi.
      2. hi <tên_biến> [độ_sâu]  : Mở bung toàn bộ member của biến/object C++.
    """

    def __init__(self, name: str = "hm-inspect"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        # Chế độ 1: Tự nhận diện ngữ cảnh hàm con hiện tại
        if not args:
            print(inspect_current_context())
            return

        # Chế độ 2: Duyệt object tổng quát theo tên
        expr = args[0]
        max_depth = int(args[1]) if len(args) > 1 else 1
        max_elems = int(args[2]) if len(args) > 2 else 10

        try:
            val = gdb.parse_and_eval(expr)
            inspector = GenericObjectInspector(max_pointer_depth=max_depth, max_elements=max_elems)
            snap = inspector.take_snapshot(val, name=expr)

            print(f"\n{c_cyan('===')} {c_bold('GENERIC INSPECT:')} {c_green(expr)} (Type: {snap.get('type_name')}) {c_cyan('===')}")
            fields = snap.get("value")
            if isinstance(fields, dict):
                for f_name, f_info in sorted(fields.items()):
                    cat = f_info.get("category", "")
                    val_str = f_info.get("raw_str", str(f_info.get("value", "")))
                    print(f"  {f_name:<28}: [{c_yellow(cat):<7}] {val_str}")
            else:
                print(f"  Value: {snap.get('raw_str')}")
            print()
        except Exception as e:
            print(f"[HM-Inspect Error]: {e}")


class CmdHmDiffCu(gdb.Command if gdb else object):
    """Render detailed RDO comparison between Best CU and Temp CU.
    Syntax: hm-diff-cu (or alias: hd)
    """

    def __init__(self, name: str = "hm-diff-cu"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        session = InspectorSession.get_instance()
        if not session.current_trial or not session.current_best:
            print("[HM-Debugger] No RDO candidate data available yet. Stop at an RDO candidate first!")
            return

        print(render_diff_table(session.current_best, session.current_trial))


class CmdHmWhere(gdb.Command if gdb else object):
    """Display current execution location within video compression call tree.
    Syntax: hm-where (or alias: hw)
    """

    def __init__(self, name: str = "hm-where"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        from gdb_scripts.core.context import get_pipeline_breadcrumb, get_current_frame_info
        fn_name, frame = get_current_frame_info()
        if not fn_name:
            print("[HM-Where] No active stack frame selected.")
            return

        lines = [
            f"\n{c_cyan('╔' + '═' * 76 + '╗')}",
            f"{c_cyan('║')} {c_bold(c_yellow('           EXECUTION PROGRESS MAP (WHERE AM I IN HM-18.0)             '))} {c_cyan('║')}",
            f"{c_cyan('╠' + '═' * 76 + '╣')}",
            f"  {c_bold('1. CURRENT FRAME:')}",
            f"     Function : {c_bold(c_green(fn_name))}",
        ]
        
        crumb = get_pipeline_breadcrumb()
        if crumb:
            lines.append(f"  {c_bold('2. CALL HIERARCHY (PIPELINE BREADCRUMB):')}")
            lines.append(f"     {crumb}")

        lines.append(f"  {c_bold('3. CTU COMPRESSION PIPELINE (7 CORE STAGES):')}")
        stages_guide = [
            ("1. compressCtu", "Initialize CTU 64x64 buffer"),
            ("2. xCompressCU", "Quadtree CU recursion (64, 32, 16, 8)"),
            ("3. xCheckRDCostIntra", "Evaluate Intra partition (SIZE_2Nx2N)"),
            ("4. estIntraPredLumaQT", "Search 35 Intra Luma modes via Hadamard & MPMs"),
            ("5. transformNxN", "Forward DCT/DST transform & quantization for TU"),
            ("6. xCheckBestMode", "Compare RD Cost (Temp vs Best) -> Pick lowest cost"),
            ("7. xCopyYuv2Pic", "Commit optimal pixels & modes to Picture buffer"),
        ]
        for name, desc in stages_guide:
            short_fn = name.split(". ")[1]
            if short_fn in fn_name:
                marker = c_bold(c_yellow("➔ "))
                lines.append(f"   {marker}{c_bold(c_green(name)):<25} : {c_yellow(desc)} {c_bold(c_yellow('(● CURRENT LOCATION)'))}")
            else:
                lines.append(f"      {c_dim(name):<25} : {c_dim(desc)}")

        lines.append(f"{c_cyan('╚' + '═' * 76 + '╝')}\n")
        print("\n".join(lines))
