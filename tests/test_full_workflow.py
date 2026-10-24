import gdb

# 1. Khởi tạo session
gdb.execute("hm-init 0 0")

# 2. Khởi chạy tiến trình HM
gdb.execute("run")

# 3. Kiểm tra các lệnh tại điểm dừng đầu tiên
print("\n--- BƯỚC 1: KIỂM TRA HM-STATUS ---")
gdb.execute("hm-status")

print("\n--- BƯỚC 2: KIỂM TRA HM-DIFF-CU ---")
gdb.execute("hm-diff-cu")

print("\n--- BƯỚC 3: KIỂM TRA HM-PRINT-GRID DEPTH ---")
gdb.execute("hm-print-grid depth --view trial")

print("\n--- BƯỚC 4: KIỂM TRA HM-PRINT-GRID INTRA ---")
gdb.execute("hm-print-grid intra --view trial")

print("\n--- BƯỚC 5: KIỂM TRA HM-INSPECT ---")
gdb.execute("hm-inspect rpcTempCU")

print("\n--- BƯỚC 6: BƯỚC SANG CANDIDATE THỨ 2 (HM-NEXT-RD) ---")
gdb.execute("hm-next-rd")
gdb.execute("hm-diff-cu")

print("\n>>> KIỂM TRA END-TO-END WORKFLOW HOÀN TOÀN THÀNH CÔNG! <<<\n")
gdb.execute("quit")
