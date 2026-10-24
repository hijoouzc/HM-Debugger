"""
gdb_scripts/commands.py
------------------------
Shim chuyển tiếp để tương thích ngược. Toàn bộ lệnh đã được module hóa trong gdb_scripts/commands/.
"""

from gdb_scripts.commands import register_all_commands

__all__ = ["register_all_commands"]
