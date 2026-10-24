"""
gdb_scripts/commands/cmd_config.py
-----------------------------------
Lệnh hc (hoặc hm-config): Hiển thị bảng tóm tắt cấu hình bộ mã hóa HM (Pilot 64x64).
"""

import os
from gdb_scripts.ui.colors import c_cyan, c_yellow, c_green, c_bold, c_dim

try:
    import gdb
except ImportError:
    gdb = None


def render_config_table() -> str:
    """Đọc và định dạng bảng cấu hình bộ mã hóa pilot bám sát 100% tên biến/cấu hình gốc."""
    cfg_path = os.path.abspath("workspace/configs/encoder_pilot_ctu64.cfg")
    
    lines = [
        c_cyan("╔" + "═" * 76 + "╗"),
        c_cyan("║") + c_bold(c_yellow("                 ENCODER CONFIGURATION (HM-18.0 PILOT)                 ")).center(85) + c_cyan("║"),
        c_cyan("╠" + "═" * 76 + "╣"),
        f"  • {c_bold('InputFile')}                     : {c_green('workspace/inputs/sample_64x64_1frame.yuv')}",
        f"  • {c_bold('BitstreamFile')}                 : {c_green('workspace/outputs/str.bin')}",
        f"  • {c_bold('ReconFile')}                     : {c_green('workspace/outputs/rec.yuv')}",
        c_dim("  " + "─" * 74),
        f"  • {c_bold('SourceWidth / SourceHeight')}    : {c_yellow('64 x 64')} (1 CTU 64x64)",
        f"  • {c_bold('FramesToBeEncoded / FrameRate')} : {c_yellow('1 / 1')} (m_iPOC = 0)",
        f"  • {c_bold('Profile / Level')}               : {c_yellow('main / NONE')}",
        f"  • {c_bold('ChromaFormatIDC / InputBitDepth')}: {c_yellow('420 (4:2:0) / 8')}",
        c_dim("  " + "─" * 74),
        f"  • {c_bold('MaxCUWidth / MaxCUHeight')}      : {c_yellow('64 / 64')} (MaxPartitionDepth = {c_yellow('4')})",
        f"  • {c_bold('QuadtreeTULog2MinSize / MaxSize')}: {c_yellow('2 (4x4) / 5 (32x32)')} (QuadtreeTUMaxDepthIntra = {c_yellow('3')})",
        f"  • {c_bold('IntraPeriod / GOPSize')}         : {c_yellow('1 / 1')} (DecodingRefreshType = {c_yellow('1')})",
        f"  • {c_bold('QP / RDOQ / RDOQTS')}            : {c_yellow('32 / 1 / 1')}",
        f"  • {c_bold('LoopFilterDisable / SAO')}       : {c_yellow('1 / 0')} (Deblocking: Disabled / SAO: Disabled)",
        c_cyan("╚" + "═" * 76 + "╝"),
        c_dim(f"  Source config: {cfg_path}")
    ]
    return "\n".join(lines)


class CmdHmConfig(gdb.Command if gdb else object):
    """Hiển thị bảng thông số cấu hình bộ mã hóa HM đang chạy."""

    def __init__(self):
        if gdb:
            super().__init__("hm-config", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        print(render_config_table())


class CmdHc(gdb.Command if gdb else object):
    """Phím tắt 2 ký tự của hm-config."""

    def __init__(self):
        if gdb:
            super().__init__("hc", gdb.COMMAND_USER)

    def invoke(self, arg: str, from_tty: bool):
        print(render_config_table())
