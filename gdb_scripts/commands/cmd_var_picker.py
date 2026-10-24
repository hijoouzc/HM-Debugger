"""
gdb_scripts/commands/cmd_var_picker.py
---------------------------------------
Interactive Variable & Object Inspector (hv / alias hm-var):
Deep hierarchical drill-down object/variable browser for HM-18.0.
Categorizes variables (Core HEVC Objects vs. Local Primitives) and lets users
explore internal class members and unpack array buffers with zero typing.
"""

from typing import List, Dict, Any, Optional, Tuple
from gdb_scripts.ui.picker import run_picker, PickerItem
from gdb_scripts.ui.colors import (
    c_cyan, c_green, c_yellow, c_bold, c_dim, c_magenta, c_red, c_inverse
)
from gdb_scripts.adapters.tcom_data_cu import (
    TComDataCUAdapter, PART_SIZE_NAMES, PRED_MODE_NAMES
)
from gdb_scripts.utils.hevc_spec_map import format_member_label, get_selective_tag
from gdb_scripts.ui.renderers import format_cost, get_intra_name

try:
    import gdb
except ImportError:
    gdb = None


CORE_VAR_NAMES = [
    "rpcTempCU",
    "rpcBestCU",
    "pCtu",
    "pcCU",
    "uiDepth",
    "uiAbsPartIdx",
    "eSize",
    "eParentPartSize",
    "rpcCoeff",
    "pcResidual"
]


def _unwrap_val_and_type(val: Any) -> Tuple[Any, Any, bool]:
    """
    Recursively unwraps C++ references and pointers to obtain the underlying concrete object.
    Returns: (dereferenced_val, stripped_type, is_null)
    """
    cur = val
    t = val.type.strip_typedefs()
    while t.code in (gdb.TYPE_CODE_REF, gdb.TYPE_CODE_RVALUE_REF, gdb.TYPE_CODE_PTR):
        if t.code in (gdb.TYPE_CODE_REF, gdb.TYPE_CODE_RVALUE_REF):
            try:
                cur = cur.referenced_value()
                t = cur.type.strip_typedefs()
            except Exception:
                return cur, t, False
        elif t.code == gdb.TYPE_CODE_PTR:
            try:
                if int(cur) == 0:
                    return cur, t, True
                cur = cur.dereference()
                t = t.target().strip_typedefs()
            except Exception:
                return cur, t, False
    return cur, t, False


def _is_primitive_type(t: Any) -> bool:
    """Check if type represents a basic numeric/boolean scalar or enum."""
    try:
        t_clean = t.strip_typedefs()
        return t_clean.code in (
            gdb.TYPE_CODE_INT,
            gdb.TYPE_CODE_FLT,
            gdb.TYPE_CODE_BOOL,
            gdb.TYPE_CODE_ENUM,
            gdb.TYPE_CODE_CHAR
        )
    except Exception:
        return False


def _is_mv_type(t: Any) -> bool:
    """Check if type represents a motion vector structure (TComMv)."""
    try:
        t_clean = str(t.strip_typedefs())
        return "TComMv" in t_clean and "TComCUMvField" not in t_clean
    except Exception:
        return False


def _classify_field(val: Any, val_type: Any) -> str:
    """
    Classify a struct field or variable into an inspection category:
    - 'NULL_PTR'
    - 'DATA_BUFFER_1D' (UChar*, SChar*, Pel*, TCoeff*, Bool*, etc.)
    - 'DATA_BUFFER_MV' (TComMv*)
    - 'DATA_BUFFER_MULTI_COMP' (UChar*[3], Pel*[3], TCoeff*[3], etc.)
    - 'DATA_BUFFER_FIXED' (int[16], etc.)
    - 'COMPOUND_ARRAY' (TComPicYuv*[5], TComCUMvField[2], etc.)
    - 'STRUCT_OR_PTR' (TComPic*, TComSlice*, TEncCu*, etc.)
    - 'SCALAR' (UInt, Int, Double, Bool, enum, etc.)
    - 'OTHER'
    """
    try:
        t_strip = val_type.strip_typedefs()
        while t_strip.code in (gdb.TYPE_CODE_REF, gdb.TYPE_CODE_RVALUE_REF):
            t_strip = t_strip.target().strip_typedefs()

        if t_strip.code == gdb.TYPE_CODE_PTR:
            try:
                if int(val) == 0:
                    return "NULL_PTR"
            except Exception:
                pass
            target = t_strip.target().strip_typedefs()
            if _is_primitive_type(target):
                return "DATA_BUFFER_1D"
            if _is_mv_type(target):
                return "DATA_BUFFER_MV"
            if target.code == gdb.TYPE_CODE_STRUCT:
                return "STRUCT_OR_PTR"
            return "OTHER"

        elif t_strip.code == gdb.TYPE_CODE_ARRAY:
            elem = t_strip.target().strip_typedefs()
            if elem.code == gdb.TYPE_CODE_PTR:
                inner = elem.target().strip_typedefs()
                if _is_primitive_type(inner):
                    return "DATA_BUFFER_MULTI_COMP"
                elif inner.code == gdb.TYPE_CODE_STRUCT:
                    return "COMPOUND_ARRAY"
            elif elem.code == gdb.TYPE_CODE_STRUCT:
                return "COMPOUND_ARRAY"
            elif _is_primitive_type(elem):
                return "DATA_BUFFER_FIXED"
            return "OTHER"

        elif t_strip.code == gdb.TYPE_CODE_STRUCT:
            return "STRUCT_OR_PTR"

        elif _is_primitive_type(t_strip):
            return "SCALAR"

    except Exception:
        pass
    return "OTHER"


def _determine_array_length(name: str, parent_val: Any, default_len: int = 64) -> int:
    """Smartly determine buffer length based on parent object context (e.g. m_uiNumPartition or TComYuv dims)."""
    try:
        # Nếu xem trực tiếp mảng pixel của CU (ví dụ m_ppcOrigYuv, m_apiBuf)
        if parent_val is not None:
            p_deref, _, is_null = _unwrap_val_and_type(parent_val)
            if not is_null and p_deref.type.strip_typedefs().code == gdb.TYPE_CODE_STRUCT:
                field_names = [f.name for f in p_deref.type.fields() if f.name]
                if "m_uiNumPartition" in field_names:
                    return int(p_deref["m_uiNumPartition"])
                if "m_iWidth" in field_names and "m_iHeight" in field_names:
                    w = int(p_deref["m_iWidth"])
                    h = int(p_deref["m_iHeight"])
                    return min(w * h, 4096)
                if "m_picWidth" in field_names:
                    w = int(p_deref["m_picWidth"])
                    h = int(p_deref["m_picHeight"])
                    return min(w * h, 4096)
    except Exception:
        pass
    return default_len


def _format_var_preview(name: str, val: Any) -> Tuple[str, str, bool]:
    """
    Format a variable for display in the picker root list.
    Returns: (label, description, is_compound)
    """
    try:
        deref_val, clean_type, is_null = _unwrap_val_and_type(val)
        type_str = str(val.type)

        if is_null:
            return f"{name}", f"nullptr ({type_str})", False

        # TComDataCU specialization
        if "TComDataCU" in str(clean_type):
            try:
                adapter = TComDataCUAdapter(val)
                if adapter.is_valid:
                    cost_str = format_cost(adapter.total_cost) if adapter.total_cost is not None else "N/A"
                    part_str = adapter.part_size_str
                    desc = f"TComDataCU* [Cost={cost_str}, Part={part_str}]"
                    return f"{name}", desc, True
            except Exception:
                pass
            try:
                return f"{name}", f"TComDataCU* (0x{int(val):x})", True
            except Exception:
                return f"{name}", f"TComDataCU* ({type_str})", True

        # Scalar / Primitive values
        if name == "uiDepth":
            d = int(deref_val)
            size = 64 >> d
            return f"{name} = {d}", f"CU Size: {size}x{size} ({type_str})", False

        kind = _classify_field(val, val.type)
        if kind == "SCALAR":
            val_clean = " ".join(str(deref_val).split())
            return f"{name} = {val_clean}", f"({type_str})", False

        if kind in ("DATA_BUFFER_1D", "DATA_BUFFER_MV", "DATA_BUFFER_MULTI_COMP", "DATA_BUFFER_FIXED"):
            return f"{name}", f"Data Buffer ({type_str})", True

        if kind == "COMPOUND_ARRAY":
            return f"{name}", f"Array of Objects ({type_str})", True

        if kind == "STRUCT_OR_PTR":
            val_clean = " ".join(str(val).split())
            if len(val_clean) > 35:
                val_clean = val_clean[:32] + "..."
            return f"{name}", f"{val_clean} ({type_str})", True

        val_str = " ".join(str(val).split())
        if len(val_str) > 35:
            val_str = val_str[:32] + "..."
        return f"{name}", f"{val_str} ({type_str})", False

    except Exception as e:
        return f"{name}", f"({e})", False


def _get_struct_fields(val: Any) -> List[PickerItem]:
    """Extract member variables and their values from a struct/class/pointer."""
    items: List[PickerItem] = []
    items.append(PickerItem("[..] < Back to Variable List", value=None, is_back=True))

    try:
        deref_val, t, is_null = _unwrap_val_and_type(val)
        if is_null:
            items.append(PickerItem("nullptr (0x0)", description="Pointer is NULL"))
            return items

        if t.code != gdb.TYPE_CODE_STRUCT:
            items.append(PickerItem(f"<Type {t} is not a struct/class>", value=None))
            return items

        fields = t.fields()
        for f in fields:
            if not f.name or f.name.startswith("_vptr"):
                continue

            try:
                member_val = deref_val[f.name]
                kind = _classify_field(member_val, f.type)

                if kind == "NULL_PTR":
                    desc = f"= nullptr ({f.type})"
                elif f.name == "m_dTotalCost":
                    cost = float(member_val)
                    desc = f"= {format_cost(cost)} ({f.type})"
                elif f.name == "m_pePartSize" and kind == "DATA_BUFFER_1D":
                    try:
                        p_val = int(member_val[0])
                        p_name = PART_SIZE_NAMES.get(p_val, str(p_val))
                        desc = f"= {p_name} ({f.type})"
                    except Exception:
                        desc = f"= Data Buffer ({f.type})"
                elif f.name == "m_pePredMode" and kind == "DATA_BUFFER_1D":
                    try:
                        p_val = int(member_val[0])
                        p_name = PRED_MODE_NAMES.get(p_val, str(p_val))
                        desc = f"= {p_name} ({f.type})"
                    except Exception:
                        desc = f"= Data Buffer ({f.type})"
                elif f.name == "m_skipFlag" and kind == "DATA_BUFFER_1D":
                    try:
                        s_val = bool(int(member_val[0]))
                        desc = f"= {'true' if s_val else 'false'} ({f.type})"
                    except Exception:
                        desc = f"= Data Buffer ({f.type})"
                elif kind == "DATA_BUFFER_1D":
                    try:
                        first_elem = int(member_val[0])
                        desc = f"= [0]={first_elem}... ({f.type})"
                    except Exception:
                        desc = f"= Data Buffer ({f.type})"
                elif kind == "DATA_BUFFER_MULTI_COMP":
                    desc = f"= Multi-Component Buffer ({f.type})"
                elif kind == "DATA_BUFFER_MV":
                    desc = f"= Motion Vector Buffer ({f.type})"
                elif kind == "COMPOUND_ARRAY":
                    desc = f"= Array of Objects ({f.type})"
                else:
                    m_val_str = " ".join(str(member_val).split())
                    if len(m_val_str) > 36:
                        m_val_str = m_val_str[:33] + "..."
                    desc = f"= {m_val_str} ({f.type})"

                display_name = format_member_label(f.name)
                items.append(PickerItem(
                    display_name,
                    value=(f.name, member_val, f.type, kind, deref_val),
                    description=desc
                ))
            except Exception as err:
                items.append(PickerItem(f.name, value=None, description=f"= <error: {err}>"))

    except Exception as e:
        items.append(PickerItem(f"<Failed to inspect fields: {e}>", value=None))

    return items


def _get_compound_array_elements(name: str, val: Any, val_type: Any, parent_val: Any) -> List[PickerItem]:
    """Generate picker items for each element of a compound array (e.g. TComPicYuv*[5] or TComCUMvField[2])."""
    items: List[PickerItem] = []
    items.append(PickerItem("[..] < Back to Object", value=None, is_back=True))

    try:
        t_strip = val_type.strip_typedefs()
        rng = t_strip.range()
        count = int(rng[1]) + 1

        YUV_NAMES = ["PIC_YUV_ORG", "PIC_YUV_REC", "PIC_YUV_TRUE_ORG", "PIC_YUV_POST_REC", "PIC_FILTERED_FG"]
        MV_NAMES = ["List 0 (L0)", "List 1 (L1)"]

        for i in range(count):
            elem = val[i]
            elem_type = t_strip.target()
            elem_kind = _classify_field(elem, elem_type)

            tag = ""
            if "TComPicYuv" in str(elem_type) and i < len(YUV_NAMES):
                tag = f" ({YUV_NAMES[i]})"
            elif "TComCUMvField" in str(elem_type) and i < len(MV_NAMES):
                tag = f" ({MV_NAMES[i]})"

            lbl = f"[{i}]{tag}"

            if elem_kind == "NULL_PTR":
                desc = f"= nullptr ({elem_type})"
            else:
                elem_str = " ".join(str(elem).split())
                if len(elem_str) > 36:
                    elem_str = elem_str[:33] + "..."
                desc = f"= {elem_str} ({elem_type})"

            items.append(PickerItem(
                lbl,
                value=(f"{name}[{i}]", elem, elem_type, elem_kind, val),
                description=desc
            ))
    except Exception as e:
        items.append(PickerItem(f"<Failed to unpack array elements: {e}>", value=None))

    return items


def _build_array_view_items(name: str, val: Any, val_type: Any, kind: str, parent_val: Any) -> List[PickerItem]:
    """Generate in-picker scrollable inspection rows and statistics for an array buffer."""
    items: List[PickerItem] = []
    items.append(PickerItem("[..] < Back to Member List", value=None, is_back=True))

    length = _determine_array_length(name, parent_val, default_len=64)

    try:
        if kind == "DATA_BUFFER_MULTI_COMP":
            t_strip = val_type.strip_typedefs()
            num_comps = int(t_strip.range()[1]) + 1
            comp_labels = ["Y / Luma", "U / Cb", "V / Cr"]

            for c_idx in range(num_comps):
                c_ptr = val[c_idx]
                c_name = comp_labels[c_idx] if c_idx < len(comp_labels) else f"Comp {c_idx}"
                items.append(PickerItem(f"Component [{c_idx}: {c_name}]", is_header=True))

                if int(c_ptr) == 0:
                    items.append(PickerItem("  nullptr (0x0)", description="Plane buffer is empty"))
                    continue

                vals = [int(c_ptr[i]) for i in range(min(length, 256))]
                min_v = min(vals) if vals else 0
                max_v = max(vals) if vals else 0
                non_zero = sum(1 for x in vals if x != 0)

                items.append(PickerItem(
                    f"  [Summary] Len={len(vals)} | Min={min_v}, Max={max_v}, NonZero={non_zero}",
                    description=""
                ))

                row_size = 16 if (max_v < 256 and min_v >= -128) else 8
                max_rows = 8
                for r in range(0, min(len(vals), max_rows * row_size), row_size):
                    end_r = min(r + row_size, len(vals))
                    chunk_str = ", ".join(f"{x:2}" for x in vals[r:end_r])
                    items.append(PickerItem(f"  [{r:3}..{end_r-1:3}]: {chunk_str}"))

                if len(vals) > max_rows * row_size:
                    rem = len(vals) - max_rows * row_size
                    items.append(PickerItem(f"  ... ({rem} more elements - select Dump to view all) ...", is_header=True))

        elif kind == "DATA_BUFFER_MV":
            vals = []
            for i in range(min(length, 256)):
                mv_obj = val[i]
                vals.append((int(mv_obj["m_iHor"]), int(mv_obj["m_iVer"])))

            non_zero_mv = sum(1 for (h, v) in vals if h != 0 or v != 0)
            items.append(PickerItem(
                f"  [Summary] Len={len(vals)} MVs | NonZero MVs={non_zero_mv}",
                description=""
            ))

            for r in range(0, min(len(vals), 64), 4):
                end_r = min(r + 4, len(vals))
                chunk_str = ", ".join(f"({h},{v})" for (h, v) in vals[r:end_r])
                items.append(PickerItem(f"  [{r:3}..{end_r-1:3}]: {chunk_str}"))

        else: # DATA_BUFFER_1D or DATA_BUFFER_FIXED
            vals = [int(val[i]) for i in range(min(length, 256))]
            min_v = min(vals) if vals else 0
            max_v = max(vals) if vals else 0
            non_zero = sum(1 for x in vals if x != 0)

            items.append(PickerItem(
                f"  [Summary] Len={len(vals)} | Min={min_v}, Max={max_v}, NonZero={non_zero}",
                description=""
            ))

            row_size = 16 if (max_v < 256 and min_v >= -128) else 8
            max_rows = 16
            for r in range(0, min(len(vals), max_rows * row_size), row_size):
                end_r = min(r + row_size, len(vals))
                chunk_str = ", ".join(f"{x:2}" for x in vals[r:end_r])
                items.append(PickerItem(f"  [{r:3}..{end_r-1:3}]: {chunk_str}"))

            if len(vals) > max_rows * row_size:
                rem = len(vals) - max_rows * row_size
                items.append(PickerItem(f"  ... ({rem} more elements - select Dump to view all) ...", is_header=True))

    except Exception as e:
        items.append(PickerItem(f"<Error reading array elements: {e}>", value=None))

    # Action item at bottom: Dump to terminal & exit
    items.append(PickerItem(
        label=">>> [Dump full array to console & exit] <<<",
        value=("__ACTION_DUMP__", name, val, val_type, kind, parent_val),
        description="Print formatted table to terminal scrollback"
    ))

    return items


def _print_full_array_dump(name: str, val: Any, val_type: Any, kind: str, parent_val: Any):
    """Render a comprehensive ANSI-colored console dump of the entire array."""
    length = _determine_array_length(name, parent_val, default_len=64)
    spec_tag = get_selective_tag(name.split("->")[-1].split(".")[-1])
    tag_str = f" {c_yellow(spec_tag.tag)}" if spec_tag else ""

    lines = [
        f"\n{c_cyan('=== ARRAY DUMP:')} {c_bold(name)}{tag_str} {c_dim(f'(Type: {val_type} | Length: {length})')} {c_cyan('===')}"
    ]

    try:
        if kind == "DATA_BUFFER_MULTI_COMP":
            t_strip = val_type.strip_typedefs()
            num_comps = int(t_strip.range()[1]) + 1
            comp_labels = ["Y / Luma", "U / Cb", "V / Cr"]

            for c_idx in range(num_comps):
                c_ptr = val[c_idx]
                c_name = comp_labels[c_idx] if c_idx < len(comp_labels) else str(c_idx)
                lines.append(f"  {c_bold(f'Component [{c_idx}: {c_name}]:')}")
                if int(c_ptr) == 0:
                    lines.append(f"    {c_dim('nullptr (0x0)')}")
                    continue

                # Trong YUV 4:2:0, kênh Chroma (1 và 2) có số điểm ảnh bằng 1/4 kênh Luma Y
                c_len = length >> 2 if (c_idx > 0 and length > 256) else length
                vals = [int(c_ptr[i]) for i in range(min(c_len, 4096))]
                min_v = min(vals) if vals else 0
                max_v = max(vals) if vals else 0
                non_zero = sum(1 for x in vals if x != 0)
                lines.append(f"    {c_dim(f'Summary: Min={min_v}, Max={max_v}, NonZero={non_zero} (Total {len(vals)} pixels)')}")

                row_size = 16 if (max_v < 256 and min_v >= -128) else 8
                for r in range(0, len(vals), row_size):
                    end_r = min(r + row_size, len(vals))
                    chunk_str = ", ".join(f"{x:3}" for x in vals[r:end_r])
                    lines.append(f"    [{r:4}..{end_r-1:4}]: {chunk_str}")

        elif kind == "DATA_BUFFER_MV":
            vals = []
            for i in range(min(length, 256)):
                mv_obj = val[i]
                vals.append((int(mv_obj["m_iHor"]), int(mv_obj["m_iVer"])))
            non_zero_mv = sum(1 for (h, v) in vals if h != 0 or v != 0)
            lines.append(f"  {c_dim(f'Summary: NonZero MVs={non_zero_mv} / {len(vals)}')}")
            for r in range(0, len(vals), 4):
                end_r = min(r + 4, len(vals))
                chunk_str = ", ".join(f"({h},{v})" for (h, v) in vals[r:end_r])
                lines.append(f"  [{r:3}..{end_r-1:3}]: {chunk_str}")

        else:
            vals = [int(val[i]) for i in range(min(length, 4096))]
            min_v = min(vals) if vals else 0
            max_v = max(vals) if vals else 0
            non_zero = sum(1 for x in vals if x != 0)
            lines.append(f"  {c_dim(f'Summary: Min={min_v}, Max={max_v}, NonZero={non_zero} / {len(vals)}')}")

            row_size = 16 if (max_v < 256 and min_v >= -128) else 8
            for r in range(0, len(vals), row_size):
                end_r = min(r + row_size, len(vals))
                chunk_str = ", ".join(f"{x:3}" for x in vals[r:end_r])
                lines.append(f"  [{r:4}..{end_r-1:4}]: {chunk_str}")

    except Exception as e:
        lines.append(f"  {c_yellow(f'<Error reading array elements: {e}>')}")

    lines.append("")
    print("\n".join(lines))


class CmdHmVar(gdb.Command if gdb else object):
    """Interactive Variable & Object Inspector with hierarchical drill-down.
    Syntax: hv [var_name] (or alias: hm-var)
    Use ↑/↓ to browse, Enter to drill-down into class members, and Esc or q to exit.
    """

    def __init__(self, name: str = "hv"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        if not gdb:
            print("[HM-Var] GDB is not available.")
            return

        try:
            frame = gdb.selected_frame()
        except Exception:
            frame = None

        if not frame:
            print(f"{c_yellow('[HM-Var] No stack frame available. Run hs or hn first!')}")
            return

        # Direct argument support (e.g. "hv pCtu" or "hv rpcTempCU")
        direct_var = arg.strip()
        if direct_var:
            try:
                target_val = gdb.parse_and_eval(direct_var)
                kind = _classify_field(target_val, target_val.type)
                if kind in ("DATA_BUFFER_1D", "DATA_BUFFER_MV", "DATA_BUFFER_MULTI_COMP", "DATA_BUFFER_FIXED"):
                    _print_full_array_dump(direct_var, target_val, target_val.type, kind, None)
                    return
                elif kind == "COMPOUND_ARRAY":
                    sub_items = _get_compound_array_elements(direct_var, target_val, target_val.type, None)
                    sub_title = f"ARRAY ELEMENTS: {direct_var} ({target_val.type})"
                    nav_stack = [(sub_title, target_val, sub_items, False)]
                elif kind == "STRUCT_OR_PTR":
                    sub_fields = _get_struct_fields(target_val)
                    sub_title = f"MEMBERS: {direct_var} ({target_val.type})"
                    nav_stack = [(sub_title, target_val, sub_fields, False)]
                else:
                    print(f"\n{c_cyan('=== VARIABLE DETAIL ===')}")
                    print(f"  {c_bold('Name')}  : {direct_var}")
                    print(f"  {c_bold('Type')}  : {target_val.type}")
                    print(f"  {c_bold('Value')} : {target_val}\n")
                    return
            except Exception as e:
                print(c_yellow(f"[HM-Var] Cannot evaluate '{direct_var}': {e}"))
                return
        else:
            # Step 1: Scan and categorize variables in current frame
            core_items: List[PickerItem] = []
            local_items: List[PickerItem] = []
            seen_names = set()

            # Find Core HEVC Objects first
            for cname in CORE_VAR_NAMES:
                try:
                    v = frame.read_var(cname)
                    lbl, desc, is_comp = _format_var_preview(cname, v)
                    core_items.append(PickerItem(
                        label=lbl,
                        value=(cname, v, is_comp),
                        description=desc
                    ))
                    seen_names.add(cname)
                except Exception:
                    pass

            # Find remaining local variables and arguments
            try:
                block = frame.block()
                while block and not block.is_static:
                    for sym in block:
                        sname = sym.name
                        if sname in seen_names or sname.startswith("__"):
                            continue
                        seen_names.add(sname)
                        try:
                            v = frame.read_var(sname)
                            lbl, desc, is_comp = _format_var_preview(sname, v)
                            local_items.append(PickerItem(
                                label=lbl,
                                value=(sname, v, is_comp),
                                description=desc
                            ))
                        except Exception:
                            pass
                    block = block.superblock
            except Exception:
                pass

            # Assemble Root Menu Items
            root_items: List[PickerItem] = []
            if core_items:
                root_items.append(PickerItem("Core HEVC Objects", is_header=True))
                root_items.extend(core_items)

            if local_items:
                root_items.append(PickerItem("Local Variables & Arguments", is_header=True))
                root_items.extend(local_items)

            if not root_items:
                print(c_yellow(f"[HM-Var] No active variables found in frame: {frame.name()}"))
                return

            frame_title = f"VARIABLES: {frame.name()}"
            # Navigation stack stores tuples of: (title, obj_val, items_list, is_root)
            nav_stack = [(frame_title, None, root_items, True)]

        while nav_stack:
            curr_title, curr_val, curr_items, is_root = nav_stack[-1]

            selected = run_picker(
                title=curr_title,
                items=curr_items,
                default_idx=1 if (not from_tty and is_root) else 0,
                is_interactive=from_tty
            )

            # If user pressed Esc, Left, or q
            if not selected:
                if len(nav_stack) > 1:
                    nav_stack.pop()
                    if not from_tty:
                        return
                    continue
                else:
                    return

            # If user selected '[..] < Back'
            if selected.is_back:
                nav_stack.pop()
                if not from_tty:
                    return
                continue

            if not selected.value:
                continue

            # Check special action (Dump full array to terminal)
            if isinstance(selected.value, tuple) and selected.value[0] == "__ACTION_DUMP__":
                _, d_name, d_val, d_type, d_kind, d_parent = selected.value
                _print_full_array_dump(d_name, d_val, d_type, d_kind, d_parent)
                return

            if is_root:
                var_name, var_val, is_compound = selected.value
                kind = _classify_field(var_val, var_val.type)

                if kind in ("DATA_BUFFER_1D", "DATA_BUFFER_MV", "DATA_BUFFER_MULTI_COMP", "DATA_BUFFER_FIXED"):
                    array_items = _build_array_view_items(var_name, var_val, var_val.type, kind, None)
                    sub_title = f"ARRAY VIEW: {var_name}"
                    nav_stack.append((sub_title, var_val, array_items, False))
                    continue
                elif kind == "COMPOUND_ARRAY":
                    sub_items = _get_compound_array_elements(var_name, var_val, var_val.type, None)
                    sub_title = f"ARRAY ELEMENTS: {var_name}"
                    nav_stack.append((sub_title, var_val, sub_items, False))
                    continue
                elif kind == "STRUCT_OR_PTR":
                    field_items = _get_struct_fields(var_val)
                    sub_title = f"MEMBERS: {var_name} ({var_val.type})"
                    nav_stack.append((sub_title, var_val, field_items, False))
                    continue
                else:
                    print(f"\n{c_cyan('=== VARIABLE DETAIL ===')}")
                    print(f"  {c_bold('Name')}  : {var_name}")
                    print(f"  {c_bold('Type')}  : {var_val.type}")
                    print(f"  {c_bold('Value')} : {var_val}\n")
                    return
            else:
                fname, fval, ftype, fkind, parent_obj = selected.value

                if fkind == "NULL_PTR":
                    print(f"\n{c_cyan('=== MEMBER DETAIL ===')}")
                    print(f"  {c_bold('Field')}  : {fname}")
                    print(f"  {c_bold('Type')}   : {ftype}")
                    print(f"  {c_bold('Value')}  : {c_yellow('nullptr (0x0)')}\n")
                    return

                elif fkind in ("DATA_BUFFER_1D", "DATA_BUFFER_MV", "DATA_BUFFER_MULTI_COMP", "DATA_BUFFER_FIXED"):
                    array_items = _build_array_view_items(fname, fval, ftype, fkind, parent_obj)
                    sub_title = f"ARRAY VIEW: {fname}"
                    nav_stack.append((sub_title, fval, array_items, False))
                    if not from_tty:
                        return
                    continue

                elif fkind == "COMPOUND_ARRAY":
                    sub_items = _get_compound_array_elements(fname, fval, ftype, parent_obj)
                    sub_title = f"ARRAY ELEMENTS: {fname}"
                    nav_stack.append((sub_title, fval, sub_items, False))
                    if not from_tty:
                        return
                    continue

                elif fkind == "STRUCT_OR_PTR":
                    sub_fields = _get_struct_fields(fval)
                    sub_title = f"MEMBERS: {fname} ({ftype})"
                    nav_stack.append((sub_title, fval, sub_fields, False))
                    if not from_tty:
                        return
                    continue

                else:
                    # Scalar / Primitive field
                    print(f"\n{c_cyan('=== MEMBER DETAIL ===')}")
                    print(f"  {c_bold('Field')}  : {fname}")
                    print(f"  {c_bold('Type')}   : {ftype}")
                    print(f"  {c_bold('Value')}  : {fval}\n")
                    return
