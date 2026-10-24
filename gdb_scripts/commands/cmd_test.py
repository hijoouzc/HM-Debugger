"""
gdb_scripts/commands/cmd_test.py
---------------------------------
Lệnh hm-test (hoặc test): Chạy bộ kiểm thử tự động ngay trong GDB.
"""

import os

try:
    import gdb
except ImportError:
    gdb = None


class CmdHmTest(gdb.Command if gdb else object):
    """Chạy bộ kiểm thử toàn diện verify_all.py ngay trong GDB.
    Cú pháp: hm-test (hoặc test)
    """

    def __init__(self, name: str = "hm-test"):
        if gdb:
            super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        test_file = os.path.abspath("./tests/verify_all.py")
        if os.path.exists(test_file):
            print(f">>> Đang thực thi {test_file}...")
            gdb.execute(f"source {test_file}")
        else:
            print(f"[HM-Test Lỗi] Không tìm thấy file {test_file}")
