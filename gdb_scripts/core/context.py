"""
gdb_scripts/core/context.py
----------------------------
Động cơ nhận diện ngữ cảnh (Context Detector):
Tự động phát hiện hàm C++ đang dừng trong GDB để trích xuất các biến trọng yếu nhất.
"""

import os
import linecache
from typing import Any, Dict, Optional, Tuple
from gdb_scripts.ui.colors import c_cyan, c_green, c_yellow, c_bold, c_dim, c_magenta
from gdb_scripts.ui.renderers import format_cost, get_intra_name

try:
    import gdb
except ImportError:
    gdb = None


def get_current_frame_info() -> Tuple[Optional[str], Optional[Any]]:
    """Lấy tên hàm và đối tượng frame hiện tại trong GDB."""
    if gdb is None:
        return None, None
    try:
        frame = gdb.selected_frame()
        if frame:
            return frame.name(), frame
    except Exception:
        pass
    return None, None


def get_frame_location_and_args(frame) -> Tuple[str, list]:
    """Trích xuất vị trí file:line và danh sách tham số truyền vào hàm hiện tại."""
    loc_str = ""
    args = []
    if not frame:
        return loc_str, args

    try:
        sal = frame.find_sal()
        if sal and sal.symtab:
            filename = sal.symtab.filename
            if "/HM-master/" in filename:
                filename = filename.split("/HM-master/")[-1]
            elif "/Video_Compression/" in filename:
                filename = filename.split("/Video_Compression/")[-1]
            loc_str = f"{filename}:{sal.line} (0x{frame.pc():x})"
        else:
            loc_str = f"0x{frame.pc():x}"
    except Exception:
        pass

    try:
        block = frame.block()
        while block:
            if block.function:
                for sym in block:
                    if sym.is_argument:
                        try:
                            val = frame.read_var(sym)
                            val_str = str(val).strip()
                            args.append((sym.name, val_str))
                        except Exception as e:
                            args.append((sym.name, f"<err: {e}>"))
                break
            block = block.superblock
    except Exception:
        pass

    return loc_str, args


def get_frame_source_snippet(frame, context_lines: int = 2) -> Optional[str]:
    """Trích xuất 3-5 dòng mã nguồn C++ quanh dòng thực thi hiện tại."""
    if not frame:
        return None
    try:
        sal = frame.find_sal()
        if not sal or not sal.symtab or sal.line <= 0:
            return None
        filepath = sal.symtab.fullname()
        if not filepath or not os.path.exists(filepath):
            return None

        current_line = sal.line
        start = max(1, current_line - context_lines)
        end = current_line + context_lines + 1

        snippet = []
        for l in range(start, end):
            line_text = linecache.getline(filepath, l).rstrip("\r\n")
            if l == current_line:
                snippet.append(f"    {c_bold(c_green('➔'))} {c_bold(c_yellow(f'{l:5d}'))} │ {c_bold(line_text)}")
            else:
                snippet.append(f"      {c_dim(f'{l:5d}')} │ {c_dim(line_text)}")
        return "\n".join(snippet)
    except Exception:
        return None


def get_pipeline_breadcrumb() -> str:
    """Xây dựng chuỗi dấu vết luồng thực thi (Breadcrumb) từ call stack hiện tại."""
    if gdb is None:
        return ""
    try:
        f = gdb.selected_frame()
        stack = []
        while f:
            name = f.name() or ""
            if "compressSlice" in name:
                stack.append("compressSlice")
            elif "compressCtu" in name:
                stack.append("compressCtu")
            elif "xCompressCU" in name:
                try:
                    d = int(f.read_var("uiDepth"))
                    stack.append(f"xCompressCU(Depth={d})")
                except Exception:
                    stack.append("xCompressCU")
            elif "xCheckRDCostIntra" in name:
                stack.append("xCheckRDCostIntra")
            elif "xCheckRDCostInter" in name:
                stack.append("xCheckRDCostInter")
            elif "xCheckRDCostMerge2Nx2N" in name:
                stack.append("xCheckRDCostMerge2Nx2N")
            elif "estIntraPredLumaQT" in name:
                stack.append("estIntraPredLumaQT")
            elif "predInterSearch" in name:
                stack.append("predInterSearch")
            elif "transformNxN" in name:
                stack.append("transformNxN")
            elif "xCheckBestMode" in name:
                stack.append("xCheckBestMode")
            elif "xCopyYuv2Pic" in name:
                stack.append("xCopyYuv2Pic")
            f = f.older()
        
        stack.reverse()
        if not stack:
            return ""
        
        curr = stack[-1]
        stack[-1] = c_bold(c_yellow(f"[● {curr}]"))
        dim_sep = c_dim(" ➔ ")
        return dim_sep.join(stack[:-1]) + (dim_sep if len(stack) > 1 else "") + stack[-1]
    except Exception:
        return ""


def inspect_current_context() -> str:
    """
    Tự động phân tích frame hiện tại và sinh chuỗi hiển thị tóm tắt các biến cốt lõi.
    """
    fn_name, frame = get_current_frame_info()
    if not fn_name or not frame:
        return "[HM-Context] No active stack frame selected."

    lines = [f"{c_cyan('===')} {c_bold('CURRENT FUNCTION CONTEXT:')} {c_green(fn_name)} {c_cyan('===')}"]
    
    crumb = get_pipeline_breadcrumb()
    if crumb:
        lines.append(f"  {c_dim('Pipeline :')} {crumb}")

    loc_str, fn_args = get_frame_location_and_args(frame)
    if loc_str:
        lines.append(f"  {c_dim('Location :')} {c_yellow(loc_str)}")
    if fn_args:
        arg_strs = []
        for a_name, a_val in fn_args:
            if len(a_val) > 42:
                a_val = a_val[:39] + "..."
            arg_strs.append(f"{c_bold(a_name)}={a_val}")
        lines.append(f"  {c_dim('Args     :')} {', '.join(arg_strs)}")

    src_snippet = get_frame_source_snippet(frame)
    if src_snippet:
        lines.append(f"  {c_dim('Source   :')}")
        lines.append(src_snippet)

    try:
        # MỐC 1: compressCtu
        if "compressCtu" in fn_name:
            pCtu = frame.read_var("pCtu")
            ctu_addr = int(pCtu["m_ctuRsAddr"]) if "m_ctuRsAddr" in [f.name for f in pCtu.type.target().fields()] else int(pCtu.dereference()["m_ctuRsAddr"])
            lines.append(f"  {c_bold('pCtu->m_ctuRsAddr')}          : {ctu_addr}")
            lines.append(f"  {c_dim('Init CTU 64x64 buffer (m_ppcBestCU, m_ppcTempCU).')}")

        # MỐC 2: xCompressCU
        elif "xCompressCU" in fn_name:
            uiDepth = int(frame.read_var("uiDepth"))
            rpcBestCU = frame.read_var("rpcBestCU")
            cu_ptr = rpcBestCU.referenced_value() if rpcBestCU.type.code == gdb.TYPE_CODE_REF else rpcBestCU
            w = 64 >> uiDepth
            lines.append(f"  {c_bold('uiDepth')}                   : {uiDepth} (CU Size: {w}x{w})")
            lines.append(f"  {c_bold('m_uiCUPelX, m_uiCUPelY')}    : X={int(cu_ptr['m_uiCUPelX'])}, Y={int(cu_ptr['m_uiCUPelY'])}")
            lines.append(f"  {c_dim('Evaluating CU quadtree split / non-split modes.')}")

        # MỐC 3: xCheckRDCostIntra
        elif "xCheckRDCostIntra" in fn_name:
            eSize = str(frame.read_var("eSize"))
            rpcTempCU = frame.read_var("rpcTempCU")
            cu_ptr = rpcTempCU.referenced_value() if rpcTempCU.type.code == gdb.TYPE_CODE_REF else rpcTempCU
            uiDepth = int(cu_ptr["m_puhDepth"][0])
            w = 64 >> uiDepth
            lines.append(f"  {c_bold('eSize (PartSize)')}          : {c_yellow(eSize)}")
            lines.append(f"  {c_bold('uiDepth')}                   : {uiDepth} (CU Size: {w}x{w})")

        # MỐC 4: estIntraPredLumaQT
        elif "estIntraPredLumaQT" in fn_name:
            pcCU = frame.read_var("pcCU")
            uiDepth = int(pcCU["m_puhDepth"][0])
            w = 64 >> uiDepth
            lines.append(f"  {c_bold('uiDepth')}                   : {uiDepth} (CU Size: {w}x{w})")
            try:
                num_rd = int(frame.read_var("numModesForFullRD"))
                rd_modes = frame.read_var("uiRdModeList")
                cand_costs = frame.read_var("CandCostList")
                if 0 < num_rd <= 35:
                    modes = [int(rd_modes[i]) for i in range(num_rd)]
                    modes_str = ", ".join(f"{m} ({get_intra_name(m)})" for m in modes)
                    lines.append(f"  {c_bold('numModesForFullRD')}         : {num_rd}")
                    lines.append(f"  {c_bold('uiRdModeList')}             : [{modes_str}]")
                    costs_str = ", ".join(f"{float(cand_costs[i]):.2f}" for i in range(min(num_rd, 4)))
                    lines.append(f"  {c_bold('CandCostList (Hadamard)')}   : [{costs_str}]")
                else:
                    lines.append(f"  {c_dim('(Entering function: 35 modes & MPMs being evaluated)')}")
            except Exception:
                lines.append(f"  {c_dim('(Entering function: 35 modes & MPMs being evaluated)')}")

        # MỐC 5: transformNxN
        elif "transformNxN" in fn_name:
            compID = str(frame.read_var("compID"))
            pcResidual = frame.read_var("pcResidual")
            rpcCoeff = frame.read_var("rpcCoeff")
            lines.append(f"  {c_bold('compID (ComponentID)')}      : {compID}")
            lines.append(f"  {c_bold('pcResidual[0]')}             : {int(pcResidual[0])}")
            lines.append(f"  {c_bold('rpcCoeff[0] (DC)')}          : {int(rpcCoeff[0])}")

        # MỐC 6: xCheckBestMode
        elif "xCheckBestMode" in fn_name:
            rpcTempCU = frame.read_var("rpcTempCU")
            rpcBestCU = frame.read_var("rpcBestCU")
            temp_ptr = rpcTempCU.referenced_value() if rpcTempCU.type.code == gdb.TYPE_CODE_REF else rpcTempCU
            best_ptr = rpcBestCU.referenced_value() if rpcBestCU.type.code == gdb.TYPE_CODE_REF else rpcBestCU
            j_temp = float(temp_ptr["m_dTotalCost"])
            j_best = float(best_ptr["m_dTotalCost"])
            lines.append(f"  {c_bold('rpcTempCU->m_dTotalCost')}   : {format_cost(j_temp)}  vs  {c_bold('rpcBestCU->m_dTotalCost')}: {format_cost(j_best)}")
            lines.append(f"  {c_dim('Type \"hd\" to view RDO candidate comparison table.')}")

        # MỐC 7: xCopyYuv2Pic
        elif "xCopyYuv2Pic" in fn_name:
            lines.append(f"  {c_green('xCopyYuv2Pic: Best CU reconstructed and copied to Picture (m_ppcRecoYuvTemp -> m_pcPicYuvRec)')}")
            lines.append(f"  {c_dim('Type \"hg\" to inspect CTU 16x16 SCU grid.')}")

        # Hàm con khác: Tự động in args
        else:
            block = frame.block()
            args = []
            for sym in block:
                if sym.is_argument:
                    args.append(f"{sym.name} = {frame.read_var(sym.name)}")
            if args:
                lines.append(f"  {c_bold('Arguments:')} " + ", ".join(args[:4]))
            lines.append(c_dim("  (Type 'info locals' or 'info args' for full symbols)"))

    except Exception as e:
        lines.append(f"  {c_yellow(f'Note: Unable to inspect context variables ({e})')}")

    return "\n".join(lines)
