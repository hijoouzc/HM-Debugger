"""
gdb_scripts/commands/cmd_view.py
---------------------------------
Lệnh hiển thị dữ liệu trực quan:
- hm-print-grid (alias: hg): In lưới 16x16 SCU của CTU
- hm-print-array (alias: ha): In mảng 1D cục bộ
- hm-print-pixels (alias: hp): In ma trận điểm ảnh Luma
"""

from gdb_scripts.core.session import InspectorSession
from gdb_scripts.adapters.tcom_data_cu import PART_SIZE_NAMES, PRED_MODE_NAMES, intra_dir_to_str
from gdb_scripts.adapters.tcom_yuv import TComYuvAdapter
from gdb_scripts.lut import ZSCAN_TO_RASTER
from gdb_scripts.ui.renderers import render_grid_16x16
from gdb_scripts.ui.colors import c_cyan, c_bold, c_yellow, c_green

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmPrintGrid(gdb.Command if gdb else object):
    """In lưới 16x16 SCU trực quan theo tọa độ raster chuẩn.
    Cú pháp: hm-print-grid [--view trial|best|committed] [--prop depth|partsize|intra|predmode]
    (hoặc alias ngắn: hg)
    """

    def __init__(self, name: str = "hm-print-grid"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        view_mode = "trial"
        prop = "depth"

        i = 0
        while i < len(args):
            if args[i] == "--view" and i + 1 < len(args):
                view_mode = args[i + 1].lower()
                i += 2
            elif args[i] == "--prop" and i + 1 < len(args):
                prop = args[i + 1].lower()
                i += 2
            else:
                i += 1

        session = InspectorSession.get_instance()
        raster_grid = ["."] * 256

        if view_mode == "committed":
            for abs_z in range(256):
                raster_idx = ZSCAN_TO_RASTER[abs_z]
                scu_data = session.committed_grid[abs_z]
                val = scu_data.get(prop, 0)
                if prop == "depth":
                    raster_grid[raster_idx] = str(val)
                elif prop == "partsize":
                    raster_grid[raster_idx] = PART_SIZE_NAMES.get(val, str(val))[:3]
                elif prop == "intra":
                    raster_grid[raster_idx] = f"{val:02d}"
                else:
                    raster_grid[raster_idx] = str(val)[:2]
            title = f"COMMITTED CTU GRID (Property: {prop.upper()})"
        else:
            cu = session.current_trial if view_mode == "trial" else session.current_best
            if not cu or not cu.is_valid:
                print(f"[HM-Debugger] No {view_mode} view data available yet. Stop at an RDO candidate first!")
                return

            for local_idx, abs_z in cu.get_partition_mappings():
                raster_idx = ZSCAN_TO_RASTER[abs_z]
                if prop == "depth":
                    v = cu.depth_list[local_idx] if local_idx < len(cu.depth_list) else 0
                    raster_grid[raster_idx] = str(v)
                elif prop == "partsize":
                    v = cu.part_size_list[local_idx] if local_idx < len(cu.part_size_list) else 0
                    raster_grid[raster_idx] = PART_SIZE_NAMES.get(v, str(v))[:3]
                elif prop == "intra":
                    v = cu.intra_dir_luma_list[local_idx] if local_idx < len(cu.intra_dir_luma_list) else 0
                    raster_grid[raster_idx] = f"{v:02d}"
                else:
                    v = cu.pred_mode_list[local_idx] if local_idx < len(cu.pred_mode_list) else 0
                    raster_grid[raster_idx] = PRED_MODE_NAMES.get(v, str(v))[:3]
            title = f"CTU GRID (View: {view_mode.upper()} | Property: {prop.upper()})"

        print(render_grid_16x16(raster_grid, title))


class CmdHmPrintArray(gdb.Command if gdb else object):
    """In mảng 1D cục bộ của CU hiện tại.
    Cú pháp: hm-print-array <depth|partsize|intra|predmode|cbf|skip> (hoặc alias: ha)
    """

    def __init__(self, name: str = "hm-print-array"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        if not args:
            print("Syntax: ha <depth|partsize|intra|predmode|cbf|skip>")
            return

        prop = args[0].lower()
        session = InspectorSession.get_instance()
        cu = session.current_trial
        if not cu or not cu.is_valid:
            print("[HM-Debugger] No trial view data available.")
            return

        arr_data = []
        name = ""
        if prop == "depth":
            name, arr_data = "m_puhDepth", cu.depth_list
        elif prop == "partsize":
            name, arr_data = "m_pePartSize", cu.part_size_list
        elif prop == "intra":
            name, arr_data = "m_puhIntraDir[0] (Luma)", cu.intra_dir_luma_list
        elif prop == "cbf":
            name, arr_data = "m_puhCbf[0]", cu.cbf_luma_raw_list
        elif prop == "skip":
            name, arr_data = "m_skipFlag", cu.skip_flag_list
        else:
            print(f"Invalid property '{prop}'. Choose from: depth, partsize, intra, cbf, skip.")
            return

        total_len = len(arr_data)
        print(f"\n=== 1D ARRAY: {name} (Size: {cu.cu_width}x{cu.cu_height} | Length: {total_len}) ===")
        chunk_size = 16 if total_len >= 16 else total_len
        for start in range(0, total_len, chunk_size):
            end = min(start + chunk_size, total_len)
            chunk = arr_data[start:end]
            indices_str = f"[{start:>3}..{end-1:>3}]: "
            vals_str = ", ".join(f"{x:>2}" for x in chunk)
            print(f"  {indices_str}{vals_str}")
        print()


class CmdHmPrintPixels(gdb.Command if gdb else object):
    """In ma trận điểm ảnh YUV (Luma Y hoặc Chroma U/V) của CU hiện tại.
    Cú pháp: hm-print-pixels [pred|orig|resi|reco] [y|u|v] [max_size=16] (hoặc alias: hp)
    Ví dụ:
      hp orig       -> In ảnh gốc kênh Y
      hp orig u     -> In ảnh gốc kênh Chroma U
      hp orig v 8   -> In ảnh gốc kênh Chroma V kích thước 8x8
      hp pred       -> In ảnh dự đoán kênh Y
      hp resi       -> In ảnh phần dư sai số
    """

    def __init__(self, name: str = "hm-print-pixels"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        args = arg.split()
        buf_type = "pred"
        comp_name = "y"
        comp_id = 0
        max_size = 16

        for a in args:
            al = a.lower()
            if al in ("orig", "pred", "temp_pred", "best", "best_pred", "resi", "temp_resi", "best_resi", "resi_best", "reco", "temp_reco", "best_reco", "reco_best"):
                buf_type = al
            elif al in ("y", "luma"):
                comp_name = "y"
                comp_id = 0
            elif al in ("u", "cb"):
                comp_name = "u"
                comp_id = 1
            elif al in ("v", "cr"):
                comp_name = "v"
                comp_id = 2
            elif al.isdigit():
                max_size = int(al)

        try:
            frame = gdb.selected_frame()
            this_ptr = frame.read_var("this")
            uiDepth = int(frame.read_var("uiDepth"))

            if buf_type in ("pred", "temp_pred"):
                yuv_obj = this_ptr["m_ppcPredYuvTemp"][uiDepth]
            elif buf_type in ("best", "best_pred"):
                yuv_obj = this_ptr["m_ppcPredYuvBest"][uiDepth]
            elif buf_type == "orig":
                yuv_obj = this_ptr["m_ppcOrigYuv"][uiDepth]
            elif buf_type in ("resi", "temp_resi"):
                yuv_obj = this_ptr["m_ppcResiYuvTemp"][uiDepth]
            elif buf_type in ("best_resi", "resi_best"):
                yuv_obj = this_ptr["m_ppcResiYuvBest"][uiDepth]
            elif buf_type in ("reco", "temp_reco"):
                yuv_obj = this_ptr["m_ppcRecoYuvTemp"][uiDepth]
            elif buf_type in ("best_reco", "reco_best"):
                yuv_obj = this_ptr["m_ppcRecoYuvBest"][uiDepth]
            else:
                print("Select buffer type: orig, pred, best, resi, reco, best_reco.")
                return

            adapter = TComYuvAdapter(yuv_obj)
            pixel_matrix = adapter.get_pixel_matrix(comp_id=comp_id, max_w=max_size, max_h=max_size)
            comp_labels = {0: "LUMA (Y)", 1: "CHROMA (U / Cb)", 2: "CHROMA (V / Cr)"}
            print(f"\n=== PIXEL MATRIX ({buf_type.upper()} | {comp_labels[comp_id]} | Depth={uiDepth}) ===")
            for row in pixel_matrix:
                print("  " + " ".join(f"{val:3}" for val in row))
            
            # Cảnh báo thông minh nếu buffer chưa tính toán xong (chứa giá trị rác bộ nhớ heap)
            if buf_type not in ("resi", "temp_resi", "best_resi"):
                flat_vals = [x for row in pixel_matrix for x in row]
                if flat_vals and (min(flat_vals) < 0 or max(flat_vals) > 1024):
                    print("  [Hint]: Vùng nhớ buffer này chưa được khởi tạo (Uninitialized Heap Memory).")
                    print("          Dùng 'hp orig' để xem ảnh gốc, hoặc bước tiếp (hs/hn) để xem sau khi tính toán.")
            print()
        except Exception as e:
            print(f"[HM-Pixels Error]: {e}")
