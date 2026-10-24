import sys
import os
import gdb

sys.path.insert(0, os.path.abspath("."))
from gdb_scripts.adapters.tcom_data_cu import TComDataCUAdapter, format_rdo_diff

print("\n[TEST] Bắt đầu kiểm thử TComDataCUAdapter trong GDB...")

# Đặt breakpoint tại entry xCheckBestMode
gdb.Breakpoint("TEncCu::xCheckBestMode")
gdb.execute("run")

frame = gdb.selected_frame()
rpcTempCU = frame.read_var("rpcTempCU")
rpcBestCU = frame.read_var("rpcBestCU")
uiDepth = int(frame.read_var("uiDepth"))

# Tạo adapter
trial_adapter = TComDataCUAdapter(rpcTempCU)
best_adapter = TComDataCUAdapter(rpcBestCU)

assert trial_adapter.is_valid, f"trial_adapter lỗi: {trial_adapter.error_msg}"
assert best_adapter.is_valid, f"best_adapter lỗi: {best_adapter.error_msg}"

print(f"[TEST] trial_adapter parsed thành công:")
print(f"       - POC            : {trial_adapter.poc}")
print(f"       - CTU RsAddr     : {trial_adapter.ctu_rs_addr}")
print(f"       - AbsZ           : {trial_adapter.abs_z_idx}")
print(f"       - NumPartition   : {trial_adapter.num_partition}")
print(f"       - CU Size        : {trial_adapter.cu_width}x{trial_adapter.cu_height}")
print(f"       - RD Cost        : {trial_adapter.total_cost:,.4f}")
print(f"       - Mảng depth len : {len(trial_adapter.depth_list)}")
print(f"       - Mảng intra len : {len(trial_adapter.intra_dir_luma_list)}")

assert len(trial_adapter.depth_list) == trial_adapter.num_partition, "Độ dài mảng depth không khớp num_partition!"
assert len(trial_adapter.intra_dir_luma_list) == trial_adapter.num_partition, "Độ dài mảng intra không khớp num_partition!"

# Kiểm tra bảng đối chiếu
diff_table = format_rdo_diff(best_adapter, trial_adapter, uiDepth)
print("\n" + diff_table + "\n")

print(">>> TẤT CẢ KIỂM THỬ TComDataCUAdapter ĐỀU THÀNH CÔNG! <<<\n")
gdb.execute("quit")
