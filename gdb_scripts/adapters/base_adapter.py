"""
gdb_scripts/adapters/base_adapter.py
------------------------------------
Lớp cơ sở trừu tượng cho mọi Adapter ngữ nghĩa HM.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    """
    Interface cơ sở cho các Adapter bóc tách ngữ nghĩa chuyên sâu của từng class C++ trong HM.
    """

    def __init__(self, gdb_val: Any):
        self.gdb_val = gdb_val

    @abstractmethod
    def extract_summary(self) -> Dict[str, Any]:
        """Trích xuất thông tin tóm tắt có ngữ nghĩa."""
        pass

    @abstractmethod
    def to_table(self) -> str:
        """Định dạng thông tin thành chuỗi bảng văn bản (Text/ASCII Table)."""
        pass
