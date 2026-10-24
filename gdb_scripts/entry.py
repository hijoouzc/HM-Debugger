"""
gdb_scripts/entry.py
--------------------
Điểm vào (Entry point) khi khởi chạy GDB session.
"""

import os
import sys

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.path.abspath("./gdb_scripts")

PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gdb
from gdb_scripts.commands import register_all_commands

# Cấu hình môi trường GDB tiêu chuẩn
gdb.execute("set pagination off")
gdb.execute("set print pretty on")
gdb.execute("set debuginfod enabled off")

# Đăng ký danh mục lệnh
register_all_commands()
