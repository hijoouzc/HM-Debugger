"""
gdb_scripts/adapters/__init__.py
--------------------------------
Package chứa các Adapter ngữ nghĩa cho các lớp đối tượng của HM-18.0.
"""
from .base_adapter import BaseAdapter
from .tcom_data_cu import TComDataCUAdapter

__all__ = ["BaseAdapter", "TComDataCUAdapter"]
