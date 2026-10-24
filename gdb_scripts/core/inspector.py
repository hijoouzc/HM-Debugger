"""
gdb_scripts/core/inspector.py
------------------------------
Lõi duyệt đối tượng tổng quát (Generic Core Object Inspector) cho GDB Python API.

Tính năng:
- Bóc tách cấu trúc struct/class C++ theo gdb.Type mà không phụ thuộc vào codec HM.
- Chụp snapshot có kiểm soát độ sâu (pointer depth limit) và chống chu trình con trỏ (cycle detection).
- So sánh (Diff) giữa 2 snapshot và phát hiện các trường/mảng thay đổi.
- An toàn bộ nhớ tuyệt đối: Không inferior calls, bắt mọi lỗi gdb.error/gdb.MemoryError.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import gdb
except ImportError:
    gdb = None


class TypeCategory(str, Enum):
    """Phân loại kiểu dữ liệu C++ cấp cao."""
    SCALAR = "SCALAR"
    ENUM = "ENUM"
    POINTER = "POINTER"
    STRUCT = "STRUCT"
    CLASS = "CLASS"
    ARRAY = "ARRAY"
    UNKNOWN = "UNKNOWN"


class DiffStatus(str, Enum):
    """Trạng thái so sánh giữa 2 giá trị snapshot."""
    MATCH = "MATCH"
    CHANGED = "CHANGED"
    ADDED = "ADDED"
    REMOVED = "REMOVED"


class DiffEntry:
    """Biểu diễn một dòng đối chiếu thuộc tính giữa 2 snapshot."""

    def __init__(self, path: str, status: DiffStatus, val_a: Any, val_b: Any, note: str = ""):
        self.path = path
        self.status = status
        self.val_a = val_a
        self.val_b = val_b
        self.note = note

    def __repr__(self) -> str:
        return f"<DiffEntry {self.path}: {self.status.value} (A={self.val_a!r}, B={self.val_b!r})>"


class GenericObjectInspector:
    """
    Lõi duyệt đối tượng C++ an toàn thông qua GDB Python API.
    """

    def __init__(self, max_pointer_depth: int = 1, max_elements: int = 256):
        self.max_pointer_depth = max_pointer_depth
        self.max_elements = max_elements

    @staticmethod
    def classify_type(gdb_type) -> TypeCategory:
        """Phân loại kiểu dữ liệu từ gdb.Type."""
        if gdb is None or gdb_type is None:
            return TypeCategory.UNKNOWN

        code = gdb_type.strip_typedefs().code
        if code in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_FLT, gdb.TYPE_CODE_BOOL, gdb.TYPE_CODE_CHAR):
            return TypeCategory.SCALAR
        elif code == gdb.TYPE_CODE_ENUM:
            return TypeCategory.ENUM
        elif code in (gdb.TYPE_CODE_PTR, gdb.TYPE_CODE_REF):
            return TypeCategory.POINTER
        elif code in (gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION):
            # Nhận diện chính xác Class C++ theo chuẩn quy ước của HEVC HM-18.0
            t_str = str(gdb_type.strip_typedefs())
            clean_name = t_str.replace("struct ", "").replace("class ", "").strip()
            if clean_name.startswith(("TCom", "TEnc", "TDec", "TApp", "SEI", "SyntaxElement")):
                return TypeCategory.CLASS
            try:
                for f in gdb_type.strip_typedefs().fields():
                    if f.name and "_vptr" in f.name:
                        return TypeCategory.CLASS
            except Exception:
                pass
            return TypeCategory.STRUCT
        elif code == gdb.TYPE_CODE_ARRAY:
            return TypeCategory.ARRAY
        return TypeCategory.UNKNOWN

    def inspect_value(
        self,
        val: Any,
        field_name: str = "",
        current_depth: int = 0,
        visited_ptrs: Optional[Set[int]] = None
    ) -> Dict[str, Any]:
        """
        Duyệt và trích xuất an toàn một gdb.Value thành cấu trúc Python dictionary thuần.
        """
        if visited_ptrs is None:
            visited_ptrs = set()

        snapshot: Dict[str, Any] = {
            "name": field_name,
            "category": TypeCategory.UNKNOWN.value,
            "type_name": "",
            "value": None,
            "raw_str": "",
            "is_null": False,
            "is_cycle": False,
        }

        if val is None or gdb is None:
            snapshot["raw_str"] = "<None>"
            return snapshot

        try:
            val_type = val.type.strip_typedefs()

            # Tự động unwrap C++ reference (TYPE_CODE_REF)
            if val_type.code == gdb.TYPE_CODE_REF:
                try:
                    val = val.referenced_value()
                    val_type = val.type.strip_typedefs()
                except Exception:
                    pass

            snapshot["type_name"] = str(val_type)
            category = self.classify_type(val_type)
            snapshot["category"] = category.value

            # 1. SCALAR & ENUM
            if category in (TypeCategory.SCALAR, TypeCategory.ENUM):
                if val_type.code == gdb.TYPE_CODE_BOOL:
                    snapshot["value"] = bool(val)
                elif val_type.code == gdb.TYPE_CODE_FLT:
                    snapshot["value"] = float(val)
                elif val_type.code == gdb.TYPE_CODE_INT:
                    snapshot["value"] = int(val)
                elif category == TypeCategory.ENUM:
                    snapshot["value"] = str(val)
                else:
                    snapshot["value"] = int(val)
                snapshot["raw_str"] = str(val)
                return snapshot

            # 2. POINTER / REFERENCE
            if category == TypeCategory.POINTER:
                ptr_addr = int(val)
                snapshot["value"] = hex(ptr_addr)
                snapshot["raw_str"] = hex(ptr_addr)

                if ptr_addr == 0:
                    snapshot["is_null"] = True
                    snapshot["raw_str"] = "0x0 (NULL)"
                    return snapshot

                if ptr_addr in visited_ptrs:
                    snapshot["is_cycle"] = True
                    snapshot["raw_str"] = f"{hex(ptr_addr)} <CYCLE DETECTED>"
                    return snapshot

                visited_ptrs.add(ptr_addr)

                # Dereference có kiểm soát độ sâu
                if current_depth < self.max_pointer_depth:
                    try:
                        deref_val = val.dereference()
                        deref_type = deref_val.type.strip_typedefs()
                        if deref_type.code in (gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION):
                            snapshot["value"] = self._inspect_struct(
                                deref_val, current_depth + 1, visited_ptrs
                            )
                    except (gdb.error, gdb.MemoryError) as e:
                        snapshot["dereferenced_error"] = str(e)

                return snapshot

            # 3. CLASS / STRUCT / UNION
            if category in (TypeCategory.STRUCT, TypeCategory.CLASS):
                snapshot["value"] = self._inspect_struct(val, current_depth, visited_ptrs)
                clean_name = str(val_type).replace("struct ", "").replace("class ", "").strip()
                prefix = "class" if category == TypeCategory.CLASS else "struct"
                snapshot["raw_str"] = f"{prefix} {clean_name}"
                return snapshot

            # 4. FIXED ARRAY
            if category == TypeCategory.ARRAY:
                snapshot["value"] = self._inspect_fixed_array(val, val_type)
                snapshot["raw_str"] = f"array of {val_type}"
                return snapshot

            # 5. Khác
            snapshot["value"] = str(val)
            snapshot["raw_str"] = str(val)

        except (gdb.error, gdb.MemoryError) as err:
            snapshot["error"] = str(err)
            snapshot["raw_str"] = f"<ERROR: {err}>"

        return snapshot

    def _inspect_struct(
        self,
        struct_val: Any,
        current_depth: int,
        visited_ptrs: Set[int]
    ) -> Dict[str, Any]:
        """Duyệt từng field trong một struct/class C++."""
        fields_dict: Dict[str, Any] = {}
        struct_type = struct_val.type.strip_typedefs()

        for f in struct_type.fields():
            if not f.name:
                continue
            if getattr(f, "is_base_class", False):
                continue

            try:
                field_val = struct_val[f.name]
                fields_dict[f.name] = self.inspect_value(
                    field_val,
                    field_name=f.name,
                    current_depth=current_depth,
                    visited_ptrs=visited_ptrs.copy()
                )
            except (gdb.error, gdb.MemoryError) as e:
                fields_dict[f.name] = {
                    "name": f.name,
                    "category": TypeCategory.UNKNOWN.value,
                    "error": str(e),
                    "raw_str": f"<ERROR: {e}>"
                }

        return fields_dict

    def _inspect_fixed_array(self, arr_val: Any, arr_type: Any) -> List[Any]:
        """Đọc mảng C++ có kích thước cố định trong struct."""
        result = []
        try:
            target_type = arr_type.target().strip_typedefs()
            is_scalar = target_type.code in (
                gdb.TYPE_CODE_INT, gdb.TYPE_CODE_FLT, gdb.TYPE_CODE_BOOL, gdb.TYPE_CODE_CHAR
            )

            range_type = arr_type.range()
            low, high = range_type[0], range_type[1]
            total_len = min(high - low + 1, self.max_elements)

            for i in range(total_len):
                elem = arr_val[i]
                if is_scalar:
                    result.append(int(elem) if target_type.code != gdb.TYPE_CODE_FLT else float(elem))
                else:
                    result.append(str(elem))
        except Exception as e:
            result.append(f"<Array read error: {e}>")

        return result

    def take_snapshot(self, val: Any, name: str = "") -> Dict[str, Any]:
        """Chụp snapshot toàn bộ object được chọn."""
        return self.inspect_value(val, field_name=name, current_depth=0, visited_ptrs=set())

    @staticmethod
    def diff_snapshots(
        snap_a: Optional[Dict[str, Any]],
        snap_b: Optional[Dict[str, Any]],
        parent_path: str = ""
    ) -> List[DiffEntry]:
        """So sánh đệ quy 2 snapshot dict."""
        diffs: List[DiffEntry] = []

        if snap_a is None and snap_b is None:
            return diffs

        if snap_a is None and snap_b is not None:
            diffs.append(DiffEntry(parent_path, DiffStatus.ADDED, None, snap_b.get("value")))
            return diffs

        if snap_a is not None and snap_b is None:
            diffs.append(DiffEntry(parent_path, DiffStatus.REMOVED, snap_a.get("value"), None))
            return diffs

        val_a = snap_a.get("value")
        val_b = snap_b.get("value")

        if isinstance(val_a, dict) and isinstance(val_b, dict):
            all_keys = sorted(set(val_a.keys()).union(val_b.keys()))
            for k in all_keys:
                sub_path = f"{parent_path}.{k}" if parent_path else k
                sub_diffs = GenericObjectInspector.diff_snapshots(
                    val_a.get(k), val_b.get(k), parent_path=sub_path
                )
                diffs.extend(sub_diffs)
            return diffs

        if val_a == val_b:
            diffs.append(DiffEntry(parent_path, DiffStatus.MATCH, val_a, val_b))
        else:
            diffs.append(DiffEntry(parent_path, DiffStatus.CHANGED, val_a, val_b))

        return diffs
