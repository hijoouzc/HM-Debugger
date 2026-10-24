"""
gdb_scripts/ui/renderers.py
----------------------------
Định dạng hiển thị trực quan (Presentation Layer):
- Bảng so sánh Auto-Diff RDO giữa Best CU và Temp CU.
- Banner mốc thực thi Pipeline Tour (Breadcrumb).
- Menu 7 mốc chuẩn của HM-18.0.
- Lưới 16x16 SCU hiển thị Depth và Intra Mode.
"""

from typing import List, Dict, Any, Optional
from gdb_scripts.ui.colors import (
    c_cyan, c_green, c_yellow, c_red, c_magenta, c_bold, c_dim, Color,
    visible_len, strip_ansi, rainbow_gradient
)

INF = float("inf")

INTRA_DIR_NAMES = {
    0: "PLANAR_IDX",
    1: "DC_IDX",
    2: "DIA_IDX",
    10: "HOR_IDX",
    26: "VER_IDX",
    34: "VDIA_IDX",
    36: "DM_CHROMA_IDX"
}

def get_intra_name(mode: int) -> str:
    if mode in INTRA_DIR_NAMES:
        return INTRA_DIR_NAMES[mode]
    elif 2 <= mode <= 34:
        return f"ANGULAR_{mode}"
    return "UNKNOWN"


def pad_line(content: str, width: int = 78) -> str:
    vis = visible_len(content)
    pad = max(0, width - 2 - vis)
    return c_cyan("│") + content + (" " * pad) + c_cyan("│")


def render_compact_context_panel(
    stage_num: int,
    total_stages: int,
    fn_sig: str,
    depth: int = 0,
    abs_z: int = 0,
    cand_idx: int = 0,
    trial=None,
    best=None,
    details: str = "",
    width: int = 78
) -> str:
    """Render khung trạng thái Compact Context Panel 4 dòng tinh gọn chuẩn HM-18.0."""
    title = f"[{stage_num}/{total_stages}] {fn_sig}"
    title_vis = visible_len(title)
    dash_count = max(0, width - 5 - title_vis)
    top_bar = c_cyan("┌─ ") + c_bold(c_yellow(title)) + c_cyan(" " + "─" * dash_count + "┐")

    cu_size = 64 >> depth
    num_parts = 256 >> (depth * 2)
    part_range = f"{abs_z}..{abs_z + num_parts - 1}" if num_parts > 1 else f"{abs_z}"
    cand_label = f"Trial Candidate #{cand_idx}" if cand_idx > 0 else "Stage Active"
    l2 = f" uiDepth: {c_yellow(str(depth))} ({cu_size}x{cu_size}) │ uiAbsPartIdx: {c_yellow(part_range)} │ {c_cyan(cand_label)}"
    mid_sep = c_cyan("├" + "─" * (width - 2) + "┤")

    if trial and trial.is_valid:
        temp_cost = trial.total_cost
        best_cost = best.total_cost if best and best.is_valid else INF
        part_str = trial.part_size_str or "SIZE_2Nx2N"
        intra_dir = trial.intra_dir_luma_list[0] if (trial.intra_dir_luma_list and len(trial.intra_dir_luma_list) > 0) else -1
        mode_str = get_intra_name(intra_dir) if intra_dir >= 0 else "UNKNOWN"

        best_part = best.part_size_str if (best and best.is_valid and best.part_size_str) else "UNKNOWN"
        best_intra = best.intra_dir_luma_list[0] if (best and best.is_valid and best.intra_dir_luma_list and len(best.intra_dir_luma_list) > 0) else -1
        best_mode = get_intra_name(best_intra) if best_intra >= 0 else "-"

        if temp_cost < best_cost:
            if best_cost >= 1e300:
                badge = c_green("✔ BETTER (-INF)")
            else:
                diff = temp_cost - best_cost
                badge = c_green(f"✔ BETTER ({diff:,.2f})")
        else:
            diff = temp_cost - best_cost
            badge = c_red(f"✖ WORSE (+{diff:,.2f})")

        l3 = f" rpcTempCU : Cost={c_yellow(format_cost(temp_cost))} │ {part_str} │ {mode_str}   ➔  {badge}"
        l4 = f" rpcBestCU : Cost={c_yellow(format_cost(best_cost))} │ {best_part} │ {best_mode}"
    else:
        l3 = f" rpcTempCU : {c_dim(details or 'm_ppcTempCU buffer active')}"
        l4 = f" rpcBestCU : {c_dim('m_ppcBestCU init (Cost = MAX_DOUBLE)')}"

    bot_bar = c_cyan("└" + "─" * (width - 2) + "┘")
    guide = f"  {c_dim('[Enter: hs]  [hn: next-rd]  [hd: diff]  [hg: grid]')}"

    lines = [
        top_bar,
        pad_line(l2, width),
        mid_sep,
        pad_line(l3, width),
        pad_line(l4, width),
        bot_bar,
        guide
    ]
    return "\n".join(lines)

def format_cost(cost: float) -> str:
    """Định dạng chi phí RD (xử lý an toàn INF / MAX_DOUBLE)."""
    if cost >= 1.0e+300 or cost == INF:
        return "INF"
    return f"{cost:,.2f}"


def format_distortion(dist: int) -> str:
    """Định dạng distortion."""
    if dist >= 10**15 or dist < 0:
        return "INF"
    return f"{dist:,}"


def render_diff_table(best, temp) -> str:
    """Render bảng so sánh chi phí RDO giữa Best CU và Temp CU."""
    d_best = best.total_distortion if best and best.is_valid else INF
    d_temp = temp.total_distortion if temp and temp.is_valid else INF

    r_best = best.total_bits if best and best.is_valid else 0
    r_temp = temp.total_bits if temp and temp.is_valid else 0

    j_best = best.total_cost if best and best.is_valid else INF
    j_temp = temp.total_cost if temp and temp.is_valid else INF

    if j_best >= 1.0e300: j_best = INF
    if j_temp >= 1.0e300: j_temp = INF
    if d_best >= 10**15 or d_best < 0: d_best = INF
    if d_temp >= 10**15 or d_temp < 0: d_temp = INF

    # Tính delta
    delta_d_str = "---"
    if d_best != INF and d_temp != INF:
        diff_d = d_temp - d_best
        delta_d_str = f"{diff_d:+d}"
    elif d_best == INF and d_temp != INF:
        delta_d_str = "-INF"

    diff_r = r_temp - r_best
    delta_r_str = f"{diff_r:+d}"

    delta_j_str = "---"
    if j_best != INF and j_temp != INF:
        diff_j = j_temp - j_best
        delta_j_str = f"{diff_j:+,.2f}"
    elif j_best == INF and j_temp != INF:
        delta_j_str = "-INF"

    # Kết luận thắng/thua
    if j_temp < j_best:
        verdict = f"{c_green('[TEMP WINS]')} rpcTempCU->getTotalCost() < rpcBestCU->getTotalCost() -> {c_bold('SWAP(rpcBestCU, rpcTempCU)')}"
    else:
        verdict = f"{c_yellow('[BEST REMAINS]')} rpcTempCU->getTotalCost() >= rpcBestCU->getTotalCost() -> {c_dim('Retain rpcBestCU')}"

    best_mode_str = f"{best.part_size_str} / {best.pred_mode_str}" if best and best.is_valid else "UNKNOWN / UNKNOWN"
    temp_mode_str = f"{temp.part_size_str} / {temp.pred_mode_str}" if temp and temp.is_valid else "UNKNOWN / UNKNOWN"

    lines = [
        c_cyan("=" * 86),
        c_bold(f"  {c_yellow('RDO TRIAL COMPARISON')}: {temp_mode_str:<26} vs  Best: {best_mode_str:<26}"),
        c_dim("-" * 86),
        f"  RD Metric                   rpcBestCU                  rpcTempCU (Candidate)   Delta",
        c_dim("-" * 86),
        f"  m_uiTotalDistortion (D)    {format_distortion(d_best):<26} {format_distortion(d_temp):<23} {delta_d_str}",
        f"  m_uiTotalBits (R)          {r_best:<26} {r_temp:<23} {delta_r_str}",
        f"  m_dTotalCost (J = D+λ·R)   {format_cost(j_best):<26} {format_cost(j_temp):<23} {delta_j_str}",
        c_dim("-" * 86),
        f"  VERDICT: {verdict}",
        c_cyan("=" * 86)
    ]
    return "\n".join(lines)


def render_stage_banner(stage_num: int, total_stages: int, stage_name: str, fn_sig: str, details: str = "", breadcrumb: str = "") -> str:
    """Render banner tiến trình trong Pipeline Tour."""
    bar = c_cyan("━" * 78)
    title = f"{c_bold(c_yellow(f'[{stage_num}/{total_stages}]'))} {c_bold(c_green(fn_sig))} {c_dim(f'- {stage_name}')}"
    lines = [
        bar,
        f"  {title}",
    ]
    if breadcrumb:
        lines.append(f"  {c_cyan('Tree:')} {c_bold(breadcrumb)}")
    if details:
        lines.append(f"  ↳ {details}")
    lines.append(c_dim("  [Press ENTER to continue to next sub-function]"))
    lines.append(bar)
    return "\n".join(lines)


def render_menu(stages: List[Dict[str, Any]], title: str = "HM-18.0 CTU ENCODING PIPELINE (7 CORE STAGES)", footer: str = "  Run: hs (step tour) | hm-trace <intra|inter|transform|split> | hm-start") -> str:
    """Render menu danh sách các giai đoạn nén của HM-18.0."""
    bar_width = 76
    lines = [
        c_cyan("╔" + "═" * bar_width + "╗"),
        c_cyan("║") + c_bold(c_yellow(f"   {title}   ")).center(bar_width + 9) + c_cyan("║"),
        c_cyan("╠" + "═" * bar_width + "╣"),
    ]
    for idx, st in enumerate(stages, 1):
        num_str = c_bold(c_green(f"  [{idx}]"))
        name_str = c_bold(f"{st['name']:<20}")
        fn_display = st['fn'] if len(st['fn']) <= 32 else st['fn'].split("::")[-1]
        fn_str = c_dim(f"{fn_display:<32}")
        desc_str = st['desc']
        lines.append(f"  {num_str} {name_str} {fn_str} - {desc_str}")
    lines.append(c_cyan("╚" + "═" * bar_width + "╝"))
    if footer:
        lines.append(c_dim(footer))
    return "\n".join(lines)


def render_grid_16x16(grid_data: List[int], title: str, formatter=lambda x: str(x)) -> str:
    """In lưới 16x16 SCU trực quan theo tọa độ raster chuẩn."""
    lines = [
        f"\n{c_cyan('===')} {c_bold(title)} {c_cyan('===')}",
        "     " + " ".join(f"{x:2}" for x in range(16)),
        "   +" + "---" * 16 + "+"
    ]
    for r in range(16):
        row_vals = [formatter(grid_data[r * 16 + c]) for c in range(16)]
        lines.append(f"{r:2} | " + " ".join(f"{v:>2}" for v in row_vals) + " |")
    lines.append("   +" + "---" * 16 + "+\n")
    return "\n".join(lines)


def render_startup_banner(target_ctu: int = 0, target_poc: int = 0) -> str:
    """Render logo và thông số phiên làm việc theo phong cách Rainbow của Antigravity CLI."""
    raw_logo = [
        "  ▄▄   ▄▄    ▄▄     ▄▄  ",
        "  ██   ██    ███   ███  ",
        "  ███████    ██ ▀▄▀ ██  ",
        "  ██   ██    ██     ██  ",
        "  ▀▀   ▀▀    ▀▀     ▀▀  "
    ]
    colored_logo = rainbow_gradient(raw_logo)
    info = [
        f"{c_bold('HM-Debugger v2.0')} {c_dim('(HEVC Test Model 18.0)')}",
        f"Target : {c_yellow(f'm_ctuRsAddr={target_ctu} (64x64)')} │ {c_yellow(f'm_iPOC={target_poc} (I-Slice)')}",
        f"Config : {c_dim('workspace/configs/encoder_pilot_ctu64.cfg')}",
        f"Keys   : {c_green('menu')} (or {c_green('h')}: palette) │ {c_green('hv')} (vars) │ {c_green('hs')} (tour)",
        f"Run    : Type {c_bold(c_yellow('run'))} (or {c_bold(c_yellow('r'))}) to begin execution."
    ]
    lines = [""]
    for l, i in zip(colored_logo, info):
        lines.append(f"{l}  {i}")
    lines.append(c_cyan("  " + "─" * 74))
    lines.append(f"  {c_dim('Command Palette:')} {c_bold(c_green('menu'))} (or {c_bold(c_green('h'))}) │ {c_dim('Variables:')} {c_green('hv')} │ {c_dim('Help:')} {c_green('hm-help')}")
    lines.append("")
    return "\n".join(lines)
