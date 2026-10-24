import sys
import os
import gdb

# Thêm đường dẫn project
sys.path.insert(0, os.path.abspath("."))
from gdb_scripts.inspector import GenericObjectInspector

print("\n[TEST] Bắt đầu kiểm thử GenericObjectInspector bên trong GDB...")

# 1. Đặt breakpoint tại TEncCu::xCheckBestMode
bp = gdb.Breakpoint("TEncCu::xCheckBestMode")
gdb.execute("run")

# 2. Khi dừng tại breakpoint, lấy frame hiện tại
frame = gdb.selected_frame()
print(f"[TEST] Đã dừng tại hàm: {frame.name()}")
assert "xCheckBestMode" in frame.name(), f"Dừng sai hàm: {frame.name()}"

# 3. Đọc biến rpcTempCU và rpcBestCU qua frame
rpcTempCU = frame.read_var("rpcTempCU")
rpcBestCU = frame.read_var("rpcBestCU")
uiDepth = int(frame.read_var("uiDepth"))

print(f"[TEST] uiDepth = {uiDepth}")
print(f"[TEST] rpcTempCU pointer: {rpcTempCU}")
print(f"[TEST] rpcBestCU pointer: {rpcBestCU}")

# 4. Sử dụng GenericObjectInspector để chụp snapshot
inspector = GenericObjectInspector(max_pointer_depth=1)
snap_temp = inspector.take_snapshot(rpcTempCU.dereference(), name="rpcTempCU")

# 5. Kiểm tra các trường then chốt trong snapshot
fields = snap_temp.get("value", {})
assert "m_ctuRsAddr" in fields, "Thiếu m_ctuRsAddr trong snapshot!"
assert "m_absZIdxInCtu" in fields, "Thiếu m_absZIdxInCtu trong snapshot!"
assert "m_uiNumPartition" in fields, "Thiếu m_uiNumPartition trong snapshot!"
assert "m_dTotalCost" in fields, "Thiếu m_dTotalCost trong snapshot!"

ctu_rs_addr = fields["m_ctuRsAddr"]["value"]
abs_z_idx = fields["m_absZIdxInCtu"]["value"]
num_part = fields["m_uiNumPartition"]["value"]
cost = fields["m_dTotalCost"]["value"]

print(f"[TEST] Extracted fields thành công:")
print(f"       - m_ctuRsAddr      = {ctu_rs_addr}")
print(f"       - m_absZIdxInCtu   = {abs_z_idx}")
print(f"       - m_uiNumPartition = {num_part}")
print(f"       - m_dTotalCost     = {cost}")

# 6. Kiểm tra an toàn: Cycle detection
p_ctu_left = fields.get("m_pCtuLeft", {})
print(f"[TEST] m_pCtuLeft status: is_null={p_ctu_left.get('is_null')}, is_cycle={p_ctu_left.get('is_cycle')}")

print("\n>>> TẤT CẢ KIỂM THỬ GENERIC OBJECT INSPECTOR TRÊN GDB LIVE ĐỀU THÀNH CÔNG! <<<\n")
gdb.execute("quit")
