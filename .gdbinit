# .gdbinit - Cấu hình nạp tự động HM-GDB-Inspector
set pagination off
set print pretty on
set debuginfod enabled off
set args -c workspace/configs/encoder_pilot_ctu64.cfg

# Nạp entry script (có guard chống nạp lặp)
python
import os
import sys
import gdb

if not getattr(gdb, "_hm_gdbinit_loaded", False):
    gdb._hm_gdbinit_loaded = True
    entry_path = os.path.abspath("./gdb_scripts/entry.py")
    if os.path.exists(entry_path):
        with open(entry_path) as f:
            code = compile(f.read(), entry_path, 'exec')
            exec(code, {'__file__': entry_path, '__name__': '__main__'})
end
