# HM-Debugger v2.0 — Bộ công cụ gỡ lỗi trực quan bộ mã hóa HEVC (HM-18.0)

Công cụ hỗ trợ phân tích, bóc tách cấu trúc dữ liệu và trực quan hóa quy trình nén video chuẩn H.265/HEVC trên phần mềm tham chiếu HM (HEVC Test Model 18.0).

- **Tác giả:** Nguyễn Văn Hội (`hijoouzc`)

---

## 1. Tính năng chính

1. **Điều hướng luồng nén (Pipeline Tour & Intra Deep Micro-Tour)**:
   - `hs` (hoặc `hm-tour`): Bước tuần tự qua 7 chặng mã hóa CTU cốt lõi trong `TEncCu`.
   - `hs intra`: Đào sâu vi mô qua 8 bước chi tiết bên trong hàm `TEncCu::xCheckRDCostIntra` (Dự đoán Luma, Biến đổi DCT/DST, Lượng tử hóa, Tái tạo, Dự đoán Chroma, CABAC Entropy, RD Cost, và So sánh Best Mode).
   - `hs back`: Tự động tua ngược (rewind) trạng thái tiến trình về bước trước đó.
   - `hs <1..8>`: Nhảy trực tiếp tới bất kỳ bước nào trong luồng.
   - Hiển thị trực tiếp 5 dòng mã nguồn C++ thực tế kèm con trỏ `➔` chỉ đúng dòng đang chạy.

2. **Duyệt cây biến đa tầng (Variable & Struct Inspector - `hv`)**:
   - Giao diện TUI tương tác (phím `↑`/`↓`, `Enter` để đào sâu, `Esc` để quay lại).
   - Tự động phân loại `Core HEVC Objects` (`rpcTempCU`, `rpcBestCU`, `pCtu`) và biến cục bộ.
   - Bóc tách mảng 1D, mảng phân vùng Quadtree và mảng điểm ảnh YUV đa thành phần.

3. **Trực quan hóa ma trận điểm ảnh (Pixel Matrix - `hp`)**:
   - `hp orig`: Xem ma trận pixel gốc kênh Luma Y.
   - `hp orig u` / `hp orig v`: Xem ma trận pixel gốc kênh màu Chroma U/V.
   - `hp pred` / `hp resi` / `hp reco`: Xem ma trận pixel dự đoán, phần dư sai số và ảnh tái tạo sau nén.

4. **Bản đồ phân vùng CTU (Topology Grid - `hg`)**:
   - Chiếu ma trận $16 \times 16$ SCU ($4 \times 4$ pixel) của khối CTU $64 \times 64$.
   - Hiển thị độ sâu phân chia Quadtree (`depth`), hướng nội suy (`intra`), kích thước phân vùng (`partsize`), hoặc chế độ (`predmode`).

5. **So sánh ứng viên RDO (Auto-Diff Decision - `hd`)**:
   - Bảng so sánh trực quan giữa ứng viên thử nghiệm (`Temp`) và cấu hình tối ưu (`Best`) theo các chỉ số: RD Cost, Bits, Distortion, QP, và Mode.

6. **Bảng lệnh nhanh (Command Palette - `menu` hoặc `h`)**:
   - Tìm kiếm và kích hoạt nhanh mọi lệnh bằng mũi tên và phím tắt chuẩn.

---

## 2. Cấu trúc dự án

```text
hm-debugger/
├── README.md                 # Tài liệu hướng dẫn sử dụng
├── Makefile                  # Tự động hóa build, test và run
├── hm                        # Script khởi chạy 1 chạm cho GDB
├── .gdbinit                  # Cấu hình nạp tự động extension Python
├── .gitignore                # Loại trừ file nhị phân và video nặng
├── workspace/configs/
│   └── encoder_pilot_ctu64.cfg  # Cấu hình mẫu CTU 64x64
├── gdb_scripts/              # Mã nguồn Python HM-Debugger
│   ├── entry.py              # Điểm khởi động chính
│   ├── adapters/             # Bộ chuyển đổi ngữ nghĩa C++ -> Python (TComDataCU, TComYuv)
│   ├── commands/             # Lệnh mở rộng GDB (hs, hv, hp, hg, hd, hi, menu,...)
│   ├── core/                 # Phân tích call stack, frame, context và RDO evaluator
│   ├── trace/                # Quản lý breakpoint động và luồng PipelineTour
│   ├── ui/                   # ANSI renderers, picker TUI, màu sắc
│   └── utils/                # Bảng tra cứu chuẩn HEVC ITU-T H.265
└── tests/                    # Bộ kiểm thử tự động 13/13 tiêu chí
    └── verify_all.py
```

---

## 3. Hướng dẫn sử dụng

### 3.1. Khởi động nhanh
```bash
# Khởi động môi trường GDB tương tác
./hm

# Hoặc chạy kiểm tra toàn bộ 13 bài test tự động
./hm test
```

### 3.2. Quy trình gỡ lỗi khuyến nghị
1. Tại dấu nhắc `(gdb)`, gõ:
   ```gdb
   (gdb) hs intra
   ```
2. Nhấn **`ENTER`** liên tục để bước qua 8 chặng vi mô trong hàm nén Intra.
3. Nếu muốn lùi lại bước trước: gõ **`hs back`** hoặc **`hs 2`**.
4. Muốn xem ảnh pixel thực tế: gõ **`hp orig 16`** hoặc **`hp reco 16`**.
5. Muốn duyệt cây biến: gõ **`hv`**.
6. Muốn xem bảng lệnh trợ giúp: gõ **`menu`** (hoặc **`h`**).
