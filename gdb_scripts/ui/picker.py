"""
gdb_scripts/ui/picker.py
-------------------------
Interactive ANSI Raw-Mode TUI Engine:
Provides an inline, flicker-free arrow-key (↑/↓) selection picker in standard Linux terminals.
Zero external dependencies (uses standard termios, tty, sys, shutil).
Guarantees 100% terminal echo and cursor restoration even upon Ctrl+C.
"""

import sys
import os
import re
import shutil
from typing import List, Dict, Any, Optional, Tuple

try:
    import termios
    import tty
    _TERMIOS_AVAILABLE = True
except ImportError:
    _TERMIOS_AVAILABLE = False

from gdb_scripts.ui.colors import (
    c_cyan, c_green, c_yellow, c_bold, c_dim, c_magenta, c_red, c_inverse
)

ANSI_RE = re.compile(r'\033\[[0-9;]*[a-zA-Z]')

def _visible_len(s: str) -> int:
    """Calculate the visible character length of a string ignoring ANSI color codes."""
    return len(ANSI_RE.sub('', s))

# Key Constants
KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"
KEY_ENTER = "ENTER"
KEY_TAB = "TAB"
KEY_ESC = "ESC"
KEY_BACKSPACE = "BACKSPACE"
KEY_QUIT = "QUIT"
KEY_UNKNOWN = "UNKNOWN"


class RawTerminal:
    """Context manager for terminal non-canonical mode with no-echo and guaranteed restoration."""
    def __init__(self, fd: int = None):
        self.fd = fd if fd is not None else sys.stdin.fileno()
        self.original_settings = None

    def __enter__(self):
        if not _TERMIOS_AVAILABLE or not sys.stdin.isatty():
            return self
        try:
            self.original_settings = termios.tcgetattr(self.fd)
            # Create customized attributes:
            # Disable ICANON (immediate 1-key input) and ECHO (suppress key echo on screen)
            # Preserve OFLAG (OPOST / ONLCR) so \n is correctly mapped to \r\n!
            mode = termios.tcgetattr(self.fd)
            mode[3] &= ~(termios.ICANON | termios.ECHO)
            mode[6][termios.VMIN] = 1
            mode[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSADRAIN, mode)
            # Hide cursor during interactive picker
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
        except Exception:
            self.original_settings = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if _TERMIOS_AVAILABLE and self.original_settings:
            try:
                # Restore original termios settings
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.original_settings)
            except Exception:
                pass
        # Always restore cursor visibility
        try:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
        except Exception:
            pass


def read_key(fd: int = None) -> str:
    """Read a single keypress or ANSI escape sequence from terminal."""
    if fd is None:
        fd = sys.stdin.fileno()

    ch1 = sys.stdin.read(1)
    if not ch1:
        return KEY_UNKNOWN

    if ch1 in ("\r", "\n"):
        return KEY_ENTER
    elif ch1 == "\t":
        return KEY_TAB
    elif ch1 == "\x7f" or ch1 == "\x08":
        return KEY_BACKSPACE
    elif ch1 in ("q", "Q"):
        return KEY_QUIT
    elif ch1 == "\x03":  # Ctrl+C
        raise KeyboardInterrupt()
    elif ch1 == "\x1b":  # ESC sequence
        ch2 = sys.stdin.read(1)
        if not ch2:
            return KEY_ESC
        if ch2 == "[":
            ch3 = sys.stdin.read(1)
            if ch3 == "A":
                return KEY_UP
            elif ch3 == "B":
                return KEY_DOWN
            elif ch3 == "C":
                return KEY_RIGHT
            elif ch3 == "D":
                return KEY_LEFT
            elif ch3 in ("1", "2", "3", "4", "5", "6", "7", "8"):
                # Handle tilde sequences like PageUp/PageDown
                sys.stdin.read(1)
                return KEY_UNKNOWN
        return KEY_ESC

    return ch1


class PickerItem:
    """Represents an item in the interactive picker."""
    def __init__(
        self,
        label: str,
        value: Any = None,
        description: str = "",
        is_header: bool = False,
        is_back: bool = False
    ):
        self.label = label
        self.value = value
        self.description = description
        self.is_header = is_header
        self.is_back = is_back


def run_picker(
    title: str,
    items: List[PickerItem],
    default_idx: int = 0,
    max_visible: int = 8,
    is_interactive: bool = True
) -> Optional[PickerItem]:
    """
    Renders an interactive arrow-key picker in the terminal with clean, borderless agy styling.
    Returns the selected PickerItem, or None if cancelled.
    """
    if not items:
        return None

    # Fallback for non-interactive / headless / batch testing environments
    if not is_interactive or not _TERMIOS_AVAILABLE or not sys.stdin.isatty():
        return _fallback_batch_picker(title, items, default_idx)

    # Filter selectable item indices (skip headers)
    selectable_indices = [i for i, it in enumerate(items) if not it.is_header]
    if not selectable_indices:
        return None

    curr_sel = default_idx
    if curr_sel not in selectable_indices:
        curr_sel = selectable_indices[0]

    last_rendered_lines = 0

    try:
        with RawTerminal():
            while True:
                # Calculate terminal dimensions
                term_cols, _ = shutil.get_terminal_size((80, 24))
                term_cols = max(40, term_cols)

                # Scroll window calculation
                total_items = len(items)
                half_vis = max_visible // 2
                start_idx = max(0, curr_sel - half_vis)
                end_idx = min(total_items, start_idx + max_visible)
                if end_idx - start_idx < max_visible:
                    start_idx = max(0, end_idx - max_visible)

                # Erase previously rendered lines cleanly from column 0
                if last_rendered_lines > 0:
                    sys.stdout.write(f"\r\033[{last_rendered_lines}A\033[J")

                # Column alignment width
                selectable_items = [it for it in items if not it.is_header]
                max_lbl_len = max((len(it.label) for it in selectable_items), default=12)
                col_width = min(max(max_lbl_len + 4, 24), max(24, min(48, term_cols // 2)))

                # Build borderless frame lines (agy style)
                lines = []
                if title:
                    lines.append(c_bold(c_cyan(f"  {title}")))

                if start_idx > 0:
                    lines.append(c_dim(f"   ↑ {start_idx} more"))

                for idx in range(start_idx, end_idx):
                    item = items[idx]
                    if item.is_header:
                        lines.append(c_bold(c_magenta(f"  {item.label}")))
                    else:
                        is_active = (idx == curr_sel)
                        cursor = c_bold(c_cyan("> ")) if is_active else "  "

                        lbl = item.label
                        if item.is_back:
                            lbl_str = c_bold(c_yellow(lbl)) if is_active else c_yellow(lbl)
                        elif is_active:
                            lbl_str = c_bold(c_green(lbl))
                        else:
                            lbl_str = lbl

                        pad_len = max(2, col_width - len(lbl))
                        pad = " " * pad_len

                        # Calculate available width for description to prevent terminal wrapping
                        prefix_vis_len = 2 + len(lbl) + pad_len
                        avail_desc = max(0, term_cols - prefix_vis_len - 1)

                        desc_text = " ".join(item.description.split()) if item.description else ""
                        if desc_text and len(desc_text) > avail_desc:
                            desc_text = desc_text[:max(0, avail_desc - 3)] + "..."

                        if desc_text:
                            line_content = f"{cursor}{lbl_str}{pad}{c_dim(desc_text)}"
                        else:
                            line_content = f"{cursor}{lbl_str}"

                        lines.append(line_content)

                if end_idx < total_items:
                    lines.append(c_dim(f"   ↓ {total_items - end_idx} more"))

                lines.append("")
                k_nav = c_bold(c_cyan("↑/↓"))
                k_enter = c_bold(c_cyan("enter"))
                k_tab = c_bold(c_cyan("tab"))
                k_esc = c_bold(c_cyan("esc"))
                lines.append(f"  {k_nav} {c_dim('Navigate · ')}{k_enter} {c_dim('Select · ')}{k_tab} {c_dim('Complete')}")
                lines.append(f"{k_esc} {c_dim('to cancel')}")

                # Output frame
                frame_text = "\n".join(lines) + "\n"
                sys.stdout.write(frame_text)
                sys.stdout.flush()
                last_rendered_lines = frame_text.count("\n")

                # Read next key
                key = read_key()
                if key == KEY_UP:
                    prev_indices = [i for i in selectable_indices if i < curr_sel]
                    if prev_indices:
                        curr_sel = prev_indices[-1]
                    else:
                        curr_sel = selectable_indices[-1]
                elif key == KEY_DOWN:
                    next_indices = [i for i in selectable_indices if i > curr_sel]
                    if next_indices:
                        curr_sel = next_indices[0]
                    else:
                        curr_sel = selectable_indices[0]
                elif key in (KEY_ENTER, KEY_TAB, KEY_RIGHT):
                    if last_rendered_lines > 0:
                        sys.stdout.write(f"\r\033[{last_rendered_lines}A\033[J")
                        sys.stdout.flush()
                    return items[curr_sel]
                elif key in (KEY_LEFT, KEY_ESC, KEY_QUIT):
                    if last_rendered_lines > 0:
                        sys.stdout.write(f"\r\033[{last_rendered_lines}A\033[J")
                        sys.stdout.flush()
                    return None

    except KeyboardInterrupt:
        if last_rendered_lines > 0:
            sys.stdout.write(f"\r\033[{last_rendered_lines}A\033[J")
            sys.stdout.flush()
        return None


def _fallback_batch_picker(
    title: str,
    items: List[PickerItem],
    default_idx: int
) -> Optional[PickerItem]:
    """Fallback static menu for non-interactive / headless batch test runs."""
    selectable = [it for it in items if not it.is_header]
    if not selectable:
        return None
    header_title = title if title else "COMMAND PALETTE"
    print(f"\n{c_cyan('=== ' + header_title + ' ===')}")
    for idx, it in enumerate(selectable):
        desc = f" - {it.description}" if it.description else ""
        print(f"  [{idx + 1}] {it.label}{desc}")
    # In batch mode, select the default or first valid item
    selected = items[default_idx] if default_idx < len(items) and not items[default_idx].is_header else selectable[0]
    print(c_dim(f"  (Batch mode auto-select: {selected.label})\n"))
    return selected
