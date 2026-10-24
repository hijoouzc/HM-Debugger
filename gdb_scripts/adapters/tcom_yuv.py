"""
gdb_scripts/adapters/tcom_yuv.py
--------------------------------
Adapter ngữ nghĩa chuyên biệt cho lớp TComYuv trong HM-18.0.
"""

from typing import Any, Dict, List, Optional
from .base_adapter import BaseAdapter


class TComYuvAdapter(BaseAdapter):
    """
    Adapter trích xuất an toàn các mặt phẳng điểm ảnh YUV từ đối tượng TComYuv.
    """

    def __init__(self, gdb_val: Any):
        super().__init__(gdb_val)
        self.is_valid = False
        self.error_msg = ""
        self.width = 0
        self.height = 0
        self.stride = 0

        self._parse()

    def _parse(self) -> None:
        val = self.gdb_val
        if val is None:
            self.error_msg = "gdb_val is None"
            return

        try:
            if val.type.strip_typedefs().code in (10, 11):  # Pointer / Ref
                if int(val) == 0:
                    self.error_msg = "Pointer is NULL"
                    return
                val = val.dereference()

            self.width = int(val["m_iWidth"])
            self.height = int(val["m_iHeight"])
            self.stride = self.width  # Với Luma kênh 0, stride == width
            self.is_valid = True
        except Exception as e:
            self.error_msg = f"Lỗi đọc TComYuv: {e}"

    def get_pixel_matrix(self, comp_id: int = 0, max_w: int = 16, max_h: int = 16) -> List[List[int]]:
        """
        Trích xuất ma trận điểm ảnh theo component (0: Y/Luma, 1: U/Cb, 2: V/Cr).
        Giới hạn max_w x max_h để tránh tràn màn hình terminal.
        """
        if not self.is_valid:
            return []

        matrix = []
        try:
            val = self.gdb_val
            if val.type.strip_typedefs().code in (10, 11):
                val = val.dereference()

            if comp_id < 0 or comp_id > 2:
                comp_id = 0

            p_buf = val["m_apiBuf"][comp_id]
            if int(p_buf) == 0:
                return []

            # Với YUV 4:2:0, kênh Chroma (1 và 2) có kích thước bằng 1/2 kênh Y
            scale_x = 1 if comp_id > 0 else 0
            scale_y = 1 if comp_id > 0 else 0
            comp_w = self.width >> scale_x
            comp_h = self.height >> scale_y
            stride = comp_w

            display_w = min(comp_w, max_w)
            display_h = min(comp_h, max_h)

            for r in range(display_h):
                row = []
                for c in range(display_w):
                    pixel_val = int(p_buf[r * stride + c])
                    row.append(pixel_val)
                matrix.append(row)
        except Exception:
            pass

        return matrix

    def get_luma_matrix(self, max_w: int = 16, max_h: int = 16, max_width: Optional[int] = None, max_height: Optional[int] = None) -> List[List[int]]:
        """
        Trích xuất ma trận điểm ảnh Luma (kênh Y = 0).
        Giữ tương thích ngược cho các lệnh cũ.
        """
        if max_width is not None:
            max_w = max_width
        if max_height is not None:
            max_h = max_height
        return self.get_pixel_matrix(comp_id=0, max_w=max_w, max_h=max_h)

    def extract_summary(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "stride": self.stride,
            "is_valid": self.is_valid,
        }

    def to_table(self) -> str:
        if not self.is_valid:
            return f"[TComYuvAdapter: INVALID - {self.error_msg}]"
        return f"TComYuv ({self.width}x{self.height}, stride={self.stride})"
