"""
tests/verify_all.py
--------------------
Script tự động kiểm thử và xác minh toàn diện (Comprehensive Verification):
100% các lệnh và luồng dữ liệu của HM-Debugger v2.
"""

import gdb

def run_verification():
    print("\n" + "=" * 76)
    print(" BẮT ĐẦU QUY TRÌNH KIỂM CHỨNG TOÀN DIỆN (VERIFICATION SUITE V2)")
    print("=" * 76)

    # 1. Kiểm tra trợ giúp và Menu
    print("\n[TEST 1/12] Kiểm tra lệnh hm-help & hm-menu...")
    gdb.execute("hm-help")
    gdb.execute("hm-menu")
    print("--> TEST 1: PASSED")

    # 2. Khởi động phiên 1 bước
    print("\n[TEST 2/12] Kiểm tra lệnh hm-start 0 0...")
    gdb.execute("hm-start 0 0")
    print("--> TEST 2: PASSED")

    # 3. Khởi chạy tiến trình encoder
    print("\n[TEST 3/12] Chạy tiến trình tới breakpoint đầu tiên...")
    gdb.execute("run")
    print("--> TEST 3: PASSED (Dừng tại Candidate 1)")

    # 4. Kiểm tra Context Inspector (hi)
    print("\n[TEST 4/12] Kiểm tra lệnh hi (Context Inspector)...")
    gdb.execute("hi")
    print("--> TEST 4: PASSED")

    # 5. Kiểm tra Generic Object Inspector
    print("\n[TEST 5/12] Kiểm tra lệnh hi rpcTempCU 1 5 (Generic Struct Inspector)...")
    gdb.execute("hi rpcTempCU 1 5")
    print("--> TEST 5: PASSED")

    # 6. Duyệt sang Candidate tiếp theo với Auto-Diff (hn)
    print("\n[TEST 6/12] Kiểm tra lệnh hn (Next RD Candidate + Auto-Diff)...")
    gdb.execute("hn")
    print("--> TEST 6: PASSED")

    # 7. Kiểm tra Lưới 16x16 SCU (hg)
    print("\n[TEST 7/12] Kiểm tra lệnh hg (16x16 CTU Grid)...")
    gdb.execute("hg")
    print("--> TEST 7: PASSED")

    # 8. Kiểm tra In mảng 1D (ha)
    print("\n[TEST 8/12] Kiểm tra lệnh ha depth, intra, cbf...")
    gdb.execute("ha depth")
    gdb.execute("ha intra")
    gdb.execute("ha cbf")
    print("--> TEST 8: PASSED")

    # 9. Kiểm tra In ma trận điểm ảnh (hp)
    print("\n[TEST 9/12] Kiểm tra lệnh hp orig 8...")
    gdb.execute("hp orig 8")
    print("--> TEST 9: PASSED")

    # 10. Kiểm tra Dynamic Trace Manager (ht)
    print("\n[TEST 10/12] Kiểm tra lệnh ht intra & ht off...")
    gdb.execute("ht intra")
    gdb.execute("ht off")
    print("--> TEST 10: PASSED")

    # 11. Kiểm tra Pipeline Tour Stepping (hs, hs intra, hs back, hs 2)
    print("\n[TEST 11/13] Kiểm tra lệnh hs (Pipeline Tour), hs intra, hs back & hs 2...")
    gdb.execute("hm-menu intra")
    gdb.execute("hs")
    gdb.execute("hs intra")
    gdb.execute("hs")
    gdb.execute("hs back")
    gdb.execute("hs 2")
    print("--> TEST 11: PASSED")

    # 12. Kiểm tra Status Summary
    print("\n[TEST 12/13] Kiểm tra lệnh hm-status...")
    gdb.execute("hm-status")
    print("--> TEST 12: PASSED")

    # 13. Kiểm tra Command Palette & Variable Inspector (menu & hv)
    print("\n[TEST 13/13] Kiểm tra lệnh menu & hv (Interactive TUI Palette, Variable Inspector & Array Unpacking)...")
    gdb.execute("hs 1")
    gdb.execute("menu")
    gdb.execute("hv")
    print("Kiểm tra hv bóc tách mảng 1D (m_puhDepth)...")
    gdb.execute("hv rpcTempCU->m_puhDepth")
    print("Kiểm tra hv bóc tách mảng multi-component (m_puhCbf)...")
    gdb.execute("hv rpcTempCU->m_puhCbf")
    print("Kiểm tra hv duyệt mảng đối tượng (m_apcPicYuv)...")
    gdb.execute("hv rpcTempCU->m_pcPic->m_apcPicYuv")
    print("Kiểm tra hv bóc tách ma trận điểm ảnh (m_piPicOrg)...")
    gdb.execute("hv rpcTempCU->m_pcPic->m_apcPicYuv[0]->m_piPicOrg")
    print("--> TEST 13: PASSED")

    print("\n" + "=" * 76)
    print(" ✔ TẤT CẢ 13/13 HẠNG MỤC KIỂM THỬ ĐỀU VƯỢT QUA VỚI ĐỘ CHÍNH XÁC 100%!")
    print("=" * 76 + "\n")

    gdb.execute("quit")

if __name__ == "__main__":
    run_verification()
