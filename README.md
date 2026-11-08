# HM-Debugger v2.0 — Gỡ lỗi trực quan bộ mã hóa HEVC (HM-18.0)

Extension GDB (Python) để quan sát cấu trúc dữ liệu và quyết định RDO bên trong bộ mã hóa tham chiếu HM-18.0, không sửa mã nguồn C++.

- **Tác giả:** Nguyễn Văn Hội (`hijoouzc`)

## 1. Yêu cầu

- Linux x86_64, GDB có hỗ trợ Python 3.
- Binary Debug `TAppEncoderStaticd` trong `HM-master/bin/` hoặc `HEVC_reference_software/bin/` (script `./hm` tự chọn).
- Fixture có sẵn: `workspace/configs/encoder_pilot_ctu64.cfg`, `workspace/inputs/sample_64x64_1frame.yuv`.

## 2. Khởi động nhanh

```bash
./hm          # Mở GDB, đã nạp extension và chạy hm-start 0 0
./hm run      # Như trên, chạy luôn tới điểm RDO đầu tiên
./hm test     # Chạy kịch bản tests/verify_all.py
```

Quy trình gợi ý trong `(gdb)`:

1. `hs intra` rồi nhấn `Enter` liên tục để đi qua các bước bên trong `xCheckRDCostIntra`.
2. `hs back` hoặc `hs <n>` để lùi / nhảy bước.
3. `hp orig 16`, `hp reco 16` để xem ma trận điểm ảnh.
4. `hv` để duyệt cây biến; `menu` (hoặc `h`) để mở bảng lệnh.

## 3. Danh mục lệnh

| Lệnh | Alias | Cú pháp | Chức năng |
| :--- | :---: | :--- | :--- |
| `hm-start` | — | `hm-start [ctu=0] [poc=0]` | Khởi tạo phiên, đặt breakpoint theo CTU/POC mục tiêu. |
| `hm-tour` | `hs` | `hs [intra\|macro\|back\|reset\|menu\|<n>]` | Đi tuần tự qua 7 mốc CTU hoặc 8 bước Intra. |
| `hv` | `hm-var` | `hv [var_name]` | Duyệt cây biến tương tác (TUI). |
| `hm-next-rd` | `hn` | `hn` | Tới ứng viên RDO kế tiếp tại `xCheckBestMode`, in bảng diff. |
| `hm-inspect` | `hi` | `hi [expr] [depth] [max_items]` | In biến theo ngữ cảnh hàm hoặc duyệt một struct. |
| `hm-diff-cu` | `hd` | `hd` | So sánh `rpcTempCU` và `rpcBestCU`. |
| `hm-print-grid` | `hg` | `hg [depth\|intra\|partsize\|predmode]` | Lưới 16×16 SCU của CTU. |
| `hm-print-array` | `ha` | `ha <depth\|partsize\|intra\|predmode\|cbf\|skip>` | Mảng 1D của CU hiện tại. |
| `hm-print-pixels` | `hp` | `hp [pred\|orig\|resi\|reco] [y\|u\|v] [max_size=16]` | Ma trận điểm ảnh. |
| `hm-trace` | `ht` | `ht <intra\|inter\|transform\|split\|all\|off>` | Bật/tắt breakpoint theo phân hệ. |
| `hm-where` | `hw` | `hw` | Vị trí hiện tại trong cây gọi hàm HM. |
| `hm-menu` | — | `hm-menu [intra]` | Danh sách mốc Macro hoặc Intra. |
| `menu` | `h` | `menu` | Bảng lệnh (Command Palette). |
| `hm-status` | — | `hm-status` | Trạng thái phiên hiện tại. |
| `hm-help` | — | `hm-help` | Trợ giúp nhanh. |

Nguồn chính xác của danh sách này: `gdb_scripts/commands/__init__.py`.

## 4. Cấu trúc thư mục

```text
Video_Compression/
├── hm, Makefile, .gdbinit    # Khởi chạy GDB
├── gdb_scripts/
│   ├── entry.py              # Điểm nạp extension
│   ├── adapters/             # Đọc TComDataCU, TComYuv
│   ├── commands/             # Các lệnh GDB
│   ├── core/                 # Context, call stack, RDO
│   ├── trace/                # Breakpoint động, PipelineTour
│   ├── ui/                   # Renderer ANSI, TUI picker
│   └── utils/                # Bảng tra HEVC
├── workspace/                # configs/, inputs/, outputs/
├── tests/verify_all.py
├── docs/                     # Tài liệu tham chiếu (xem docs/README.md)
├── HEVC_reference_software/  # HM-18.0 + Web Analyzer (README riêng)
└── HM-master/                # HM-18.0 gốc + tài liệu TComPicSym
```

> [!NOTE]
> `tests/verify_all.py` hiện chỉ gọi lần lượt các lệnh và in `PASSED`, chưa có assertion. Kết quả chỉ cho biết lệnh chạy không lỗi.
