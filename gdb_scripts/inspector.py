"""
gdb_scripts/inspector.py
------------------------
Shim chuyển tiếp để tương thích ngược với code cũ.
"""

from gdb_scripts.core.inspector import (
    GenericObjectInspector, TypeCategory, DiffStatus, DiffEntry
)

__all__ = [
    "GenericObjectInspector", "TypeCategory", "DiffStatus", "DiffEntry"
]
