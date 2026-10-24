"""
gdb_scripts/ui/colors.py
-------------------------
Tiện ích định dạng màu sắc ANSI và biểu tượng terminal.
Tự động phát hiện terminal tty và tôn trọng biến môi trường NO_COLOR.
"""

import os
import sys

def _should_use_color() -> bool:
    """Xác định xem môi trường có hỗ trợ màu ANSI hay không.
    Lưu ý: Trong GDB Python, sys.stdout là gdb._GdbFile và luôn trả về isatty() == False!
    Do đó cần kiểm tra qua file descriptor hệ thống os.isatty(1) hoặc sys.__stdout__.
    """
    if os.environ.get("NO_COLOR", "").strip():
        return False
    if os.environ.get("FORCE_COLOR", "").strip():
        return True
    try:
        if hasattr(os, "isatty") and os.isatty(1):
            return True
        if hasattr(sys, "__stdout__") and sys.__stdout__ and hasattr(sys.__stdout__, "isatty") and sys.__stdout__.isatty():
            return True
    except Exception:
        pass
    term = os.environ.get("TERM", "")
    if term and term != "dumb":
        return True
    return True

_USE_COLOR = _should_use_color()

class Color:
    RESET   = "\033[0m" if _USE_COLOR else ""
    BOLD    = "\033[1m" if _USE_COLOR else ""
    DIM     = "\033[2m" if _USE_COLOR else ""
    UNDERLINE = "\033[4m" if _USE_COLOR else ""
    INVERSE = "\033[7m" if _USE_COLOR else ""

    # Màu chữ cơ bản
    RED     = "\033[31m" if _USE_COLOR else ""
    GREEN   = "\033[32m" if _USE_COLOR else ""
    YELLOW  = "\033[33m" if _USE_COLOR else ""
    BLUE    = "\033[34m" if _USE_COLOR else ""
    MAGENTA = "\033[35m" if _USE_COLOR else ""
    CYAN    = "\033[36m" if _USE_COLOR else ""
    WHITE   = "\033[37m" if _USE_COLOR else ""

    # Màu chữ sáng (Bright / High Intensity)
    B_RED     = "\033[91m" if _USE_COLOR else ""
    B_GREEN   = "\033[92m" if _USE_COLOR else ""
    B_YELLOW  = "\033[93m" if _USE_COLOR else ""
    B_BLUE    = "\033[94m" if _USE_COLOR else ""
    B_MAGENTA = "\033[95m" if _USE_COLOR else ""
    B_CYAN    = "\033[96m" if _USE_COLOR else ""
    B_WHITE   = "\033[97m" if _USE_COLOR else ""


def colorize(text: str, color_code: str) -> str:
    """Bao bọc chuỗi trong mã màu ANSI."""
    if not _USE_COLOR:
        return text
    return f"{color_code}{text}{Color.RESET}"


def c_cyan(text: str) -> str: return colorize(text, Color.B_CYAN)
def c_green(text: str) -> str: return colorize(text, Color.B_GREEN)
def c_yellow(text: str) -> str: return colorize(text, Color.B_YELLOW)
def c_red(text: str) -> str: return colorize(text, Color.B_RED)
def c_magenta(text: str) -> str: return colorize(text, Color.B_MAGENTA)
def c_bold(text: str) -> str: return colorize(text, Color.BOLD)
def c_dim(text: str) -> str: return colorize(text, Color.DIM)
def c_inverse(text: str) -> str: return colorize(text, Color.INVERSE)

import re
from typing import List, Tuple

# Bảng mã màu Gradient Cầu vồng chuẩn Google AI / Antigravity CLI
AGY_RAINBOW_STOPS: List[Tuple[int, int, int]] = [
    (168, 85, 247),   # Purple (#A855F7)
    (99, 102, 241),   # Indigo (#6366F1)
    (59, 130, 246),   # Sky Blue (#3B82F6)
    (20, 184, 166),   # Teal (#14B8A6)
    (34, 197, 94),    # Emerald Green (#22C55E)
    (234, 179, 8),    # Yellow (#EAB308)
    (249, 115, 22),   # Orange (#F97316)
    (236, 72, 153),   # Pink (#EC4899)
]

def rainbow_gradient(text_lines: List[str], stops: List[Tuple[int, int, int]] = AGY_RAINBOW_STOPS) -> List[str]:
    """Tô màu gradient cầu vồng Antigravity từng ký tự theo hướng chéo."""
    if not _USE_COLOR:
        return text_lines
    w = max(len(l) for l in text_lines) if text_lines else 1
    h = len(text_lines)
    result = []
    n = len(stops) - 1
    for y, line in enumerate(text_lines):
        row = []
        for x, ch in enumerate(line):
            if ch == " ":
                row.append(" ")
            else:
                t = max(0.0, min(1.0, (x / w) * 0.75 + (y / h) * 0.25))
                idx = t * n
                i = int(idx)
                f = idx - i
                if i >= n:
                    r, g, b = stops[-1]
                else:
                    r1, g1, b1 = stops[i]
                    r2, g2, b2 = stops[i + 1]
                    r = int(r1 + (r2 - r1) * f)
                    g = int(g1 + (g2 - g1) * f)
                    b = int(b1 + (b2 - b1) * f)
                row.append(f"\033[38;2;{r};{g};{b}m{ch}{Color.RESET}")
        result.append("".join(row))
    return result

def strip_ansi(text: str) -> str:
    """Loại bỏ mã ANSI để tính toán độ dài hiển thị trực quan (visible width)."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

def visible_len(text: str) -> int:
    """Độ dài chuỗi hiển thị thực tế trên terminal."""
    return len(strip_ansi(text))
