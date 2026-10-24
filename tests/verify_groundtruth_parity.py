"""
tests/verify_groundtruth_parity.py
-----------------------------------
Kiểm tra tính đồng bộ (Synchronization) và tính toàn vẹn (Integrity):
So sánh đầu ra bitstream và reconstruction giữa:
1. HM chạy độc lập (Groundtruth).
2. HM chạy dưới sự giám sát toàn phần của HM-Debugger v2.
"""

import gdb
import os
import hashlib

def get_file_md5(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def test_groundtruth_parity():
    print("\n" + "=" * 76)
    print(" KIỂM THỬ ĐỒNG BỘ & ĐỐI CHIẾU GROUNDTRUTH (ZERO-DRIFT VERIFICATION)")
    print("=" * 76)

    # 1. Khởi động inspector với target CTU 0 POC 0
    gdb.execute("hm-start 0 0")

    # Đếm số candidate được bắt
    trial_count = 0
    commit_count = 0

    print("\n>>> Đang chạy encoder dưới sự giám sát của GDB...")
    gdb.execute("run")

    # Lặp qua toàn bộ các candidate của CTU cho đến khi inferior hoàn tất
    while True:
        try:
            inf = gdb.selected_inferior()
            if not inf or inf.pid == 0:
                break
            
            frame = gdb.selected_frame()
            fname = frame.name() or ""
            
            if "xCheckBestMode" in fname:
                trial_count += 1
            elif "xCopyYuv2Pic" in fname:
                commit_count += 1
            
            gdb.execute("continue")
        except gdb.error as err:
            # Inferior đã hoàn tất bình thường
            break

    print(f"\n[GDB Telemetry] Bắt được {trial_count} lần thử nghiệm RDO và {commit_count} lần Commit.")

    # Kiểm tra Committed Grid 16x16
    print("\n>>> Trạng thái Lưới Committed cuối cùng:")
    gdb.execute("hg --view committed")

    # Đối chiếu mã băm MD5 của bitstream và reconstruction
    gt_str = "workspace/outputs/groundtruth_str.bin"
    run_str = "workspace/outputs/str.bin"

    gt_rec = "workspace/outputs/groundtruth_rec.yuv"
    run_rec = "workspace/outputs/rec.yuv"

    md5_gt_str = get_file_md5(gt_str)
    md5_run_str = get_file_md5(run_str)

    md5_gt_rec = get_file_md5(gt_rec)
    md5_run_rec = get_file_md5(run_rec)

    print("\n" + "=" * 76)
    print(" KẾT QUẢ ĐỐI CHIẾU MÃ BĂM NHỊ PHÂN (BIT-EXACT COMPARISON):")
    print("=" * 76)
    print(f"  Bitstream (str.bin)        MD5 Groundtruth : {md5_gt_str}")
    print(f"                             MD5 Inspector   : {md5_run_str}")
    match_str = (md5_gt_str == md5_run_str and md5_gt_str != "")
    print(f"  --> Khớp bitstream 100%   : {'[PASSED] ĐỒNG BỘ TUYỆT ĐỐI' if match_str else '[FAILED]'}")

    print(f"\n  Reconstruction (rec.yuv)   MD5 Groundtruth : {md5_gt_rec}")
    print(f"                             MD5 Inspector   : {md5_run_rec}")
    match_rec = (md5_gt_rec == md5_run_rec and md5_gt_rec != "")
    print(f"  --> Khớp reconstruction 100%: {'[PASSED] ĐỒNG BỘ TUYỆT ĐỐI' if match_rec else '[FAILED]'}")

    assert match_str, "Bitstream MD5 mismatch!"
    assert match_rec, "Reconstruction MD5 mismatch!"
    assert trial_count > 0, "No RDO trial captured!"
    assert commit_count > 0, "No Commit captured!"

    print("\n" + "=" * 76)
    print(" ✔ KẾT LUẬN: KHÔNG CÓ BẤT KỲ SAI LỆCH LOGIC HOẶC LỖI ĐỒNG BỘ NÀO!")
    print("   Bộ công cụ hoàn toàn Zero-Invasive và phản ánh 100% trung thực HM gốc.")
    print("=" * 76 + "\n")

    gdb.execute("quit")

if __name__ == "__main__":
    test_groundtruth_parity()
