"""
gdb_scripts/adapters/tcom_data_cu.py
------------------------------------
Adapter ngữ nghĩa chuyên biệt cho lớp TComDataCU trong HM-18.0.
"""

from typing import Any, Dict, List, Optional, Tuple
from .base_adapter import BaseAdapter

PART_SIZE_NAMES = {
    0: "SIZE_2Nx2N",
    1: "SIZE_2NxN",
    2: "SIZE_Nx2N",
    3: "SIZE_NxN",
    4: "SIZE_2NxnU",
    5: "SIZE_2NxnD",
    6: "SIZE_nLx2N",
    7: "SIZE_nRx2N",
}

PRED_MODE_NAMES = {
    0: "MODE_INTER",
    1: "MODE_INTRA",
}


def intra_dir_to_str(mode: int) -> str:
    """Chuyển đổi chỉ số hướng Intra Luma thành tên chuẩn theo HEVC HM-18.0 (CommonDef.h)."""
    if mode == 0:
        return "0 (PLANAR_IDX)"
    elif mode == 1:
        return "1 (DC_IDX)"
    elif mode == 2:
        return "2 (DIA_IDX)"
    elif mode == 10:
        return "10 (HOR_IDX)"
    elif mode == 26:
        return "26 (VER_IDX)"
    elif mode == 34:
        return "34 (VDIA_IDX)"
    elif mode == 36:
        return "36 (DM_CHROMA_IDX)"
    elif 2 <= mode <= 34:
        return f"{mode} (ANGULAR_{mode})"
    return f"{mode} (UNKNOWN)"


class TComDataCUAdapter(BaseAdapter):
    """
    Adapter đọc và bóc tách các trường dữ liệu của TComDataCU trong HM-18.0.
    
    Đảm bảo:
    - Đọc POC an toàn qua m_pcSlice->m_iPOC.
    - Giới hạn mọi vòng lặp đọc mảng theo đúng m_uiNumPartition của CU hiện tại.
    - Ánh xạ chính xác hai lớp Z-scan: local index (0..numPart-1) -> absolute CTU index.
    """

    def __init__(self, gdb_val: Any):
        super().__init__(gdb_val)
        self.is_valid = False
        self.error_msg = ""

        # Các thuộc tính scalar
        self.ctu_rs_addr: int = 0
        self.abs_z_idx: int = 0
        self.num_partition: int = 0
        self.poc: int = -1
        self.total_cost: float = float("inf")
        self.total_distortion: int = 0
        self.total_bits: int = 0
        self.cu_width: int = 0
        self.cu_height: int = 0

        # Mảng dữ liệu cục bộ (độ dài num_partition)
        self.depth_list: List[int] = []
        self.part_size_list: List[int] = []
        self.pred_mode_list: List[int] = []
        self.skip_flag_list: List[bool] = []
        self.intra_dir_luma_list: List[int] = []
        self.cbf_luma_raw_list: List[int] = []

        self._parse()

    def _parse(self) -> None:
        """Trích xuất toàn bộ trường an toàn từ gdb.Value."""
        val = self.gdb_val
        if val is None:
            self.error_msg = "gdb_val is None"
            return

        try:
            # Nếu truyền vào là pointer (TComDataCU*), dereference trước
            if val.type.strip_typedefs().code in (10, 11):  # TYPE_CODE_PTR / REF
                if int(val) == 0:
                    self.error_msg = "Pointer is NULL (0x0)"
                    return
                val = val.dereference()

            self.ctu_rs_addr = int(val["m_ctuRsAddr"])
            self.abs_z_idx = int(val["m_absZIdxInCtu"])
            self.num_partition = int(val["m_uiNumPartition"])
            self.total_cost = float(val["m_dTotalCost"])
            self.total_distortion = int(val["m_uiTotalDistortion"])
            self.total_bits = int(val["m_uiTotalBits"])

            # Đọc POC an toàn qua m_pcSlice
            slice_ptr = val["m_pcSlice"]
            if int(slice_ptr) != 0:
                self.poc = int(slice_ptr["m_iPOC"])

            # Đọc kích thước pixel
            width_ptr = val["m_puhWidth"]
            height_ptr = val["m_puhHeight"]
            if int(width_ptr) != 0 and int(height_ptr) != 0:
                self.cu_width = int(width_ptr[0])
                self.cu_height = int(height_ptr[0])

            # Đọc mảng cục bộ có độ dài đúng bằng num_partition
            p_depth = val["m_puhDepth"]
            p_part_size = val["m_pePartSize"]
            p_pred_mode = val["m_pePredMode"]
            p_skip_flag = val["m_skipFlag"]
            p_intra_dir = val["m_puhIntraDir"][0]  # Luma
            p_cbf_luma = val["m_puhCbf"][0]        # Luma CBF raw byte

            for i in range(self.num_partition):
                if int(p_depth) != 0:
                    self.depth_list.append(int(p_depth[i]))
                if int(p_part_size) != 0:
                    self.part_size_list.append(int(p_part_size[i]))
                if int(p_pred_mode) != 0:
                    self.pred_mode_list.append(int(p_pred_mode[i]))
                if int(p_skip_flag) != 0:
                    self.skip_flag_list.append(bool(p_skip_flag[i]))
                if int(p_intra_dir) != 0:
                    self.intra_dir_luma_list.append(int(p_intra_dir[i]))
                if int(p_cbf_luma) != 0:
                    self.cbf_luma_raw_list.append(int(p_cbf_luma[i]))

            self.is_valid = True

        except Exception as e:
            self.error_msg = f"Lỗi bóc tách TComDataCU: {e}"

    @property
    def part_size_str(self) -> str:
        if self.part_size_list:
            return PART_SIZE_NAMES.get(self.part_size_list[0], "UNKNOWN")
        return "UNKNOWN"

    @property
    def pred_mode_str(self) -> str:
        if self.pred_mode_list:
            return PRED_MODE_NAMES.get(self.pred_mode_list[0], "UNKNOWN")
        return "UNKNOWN"

    def extract_summary(self) -> Dict[str, Any]:
        """Trả về cấu trúc dictionary tóm tắt các thuộc tính cốt lõi."""
        return {
            "poc": self.poc,
            "ctu_rs_addr": self.ctu_rs_addr,
            "abs_z_idx": self.abs_z_idx,
            "num_partition": self.num_partition,
            "cu_width": self.cu_width,
            "cu_height": self.cu_height,
            "total_cost": self.total_cost,
            "total_distortion": self.total_distortion,
            "total_bits": self.total_bits,
            "pred_mode_0": PRED_MODE_NAMES.get(self.pred_mode_list[0], str(self.pred_mode_list[0])) if self.pred_mode_list else "N/A",
            "part_size_0": PART_SIZE_NAMES.get(self.part_size_list[0], str(self.part_size_list[0])) if self.part_size_list else "N/A",
            "intra_dir_0": intra_dir_to_str(self.intra_dir_luma_list[0]) if self.intra_dir_luma_list else "N/A",
            "is_valid": self.is_valid,
        }

    def get_partition_mappings(self) -> List[Tuple[int, int]]:
        """
        Sinh cặp danh sách ánh xạ hai lớp: (local_idx, ctu_abs_z_idx).
        Đảm bảo Z_abs = abs_z_idx + local_idx.
        """
        return [(i, self.abs_z_idx + i) for i in range(self.num_partition)]

    def to_table(self) -> str:
        """Định dạng thông tin CU thành chuỗi bảng văn bản."""
        if not self.is_valid:
            return f"[TComDataCUAdapter: INVALID - {self.error_msg}]"

        lines = [
            f"=== TComDataCU State (CTU: {self.ctu_rs_addr}, POC: {self.poc}) ===",
            f"  CU Size        : {self.cu_width}x{self.cu_height} (Partitions: {self.num_partition})",
            f"  Z-Scan Range   : {self.abs_z_idx} .. {self.abs_z_idx + self.num_partition - 1}",
            f"  Total RD-Cost  : {self.total_cost:,.4f}",
            f"  Distortion     : {self.total_distortion:,}",
            f"  Total Bits     : {self.total_bits:,}",
        ]
        if self.pred_mode_list:
            lines.append(f"  Prediction Mode: {PRED_MODE_NAMES.get(self.pred_mode_list[0], str(self.pred_mode_list[0]))}")
        if self.part_size_list:
            lines.append(f"  Partition Size : {PART_SIZE_NAMES.get(self.part_size_list[0], str(self.part_size_list[0]))}")
        if self.intra_dir_luma_list:
            lines.append(f"  Luma Intra Dir : {intra_dir_to_str(self.intra_dir_luma_list[0])}")

        return "\n".join(lines)


def format_rdo_diff(best: TComDataCUAdapter, trial: TComDataCUAdapter, ui_depth: int) -> str:
    """
    Tạo bảng đối chiếu RDO Candidate (Trial vs Current Best) trực quan, chuẩn xác.
    """
    title = f"RDO CANDIDATE COMPARISON | CTU: {trial.ctu_rs_addr} | Depth: {ui_depth} ({trial.cu_width}x{trial.cu_height}) | Z-Scan: {trial.abs_z_idx}..{trial.abs_z_idx + trial.num_partition - 1}"
    sep = "=" * len(title)

    # Đánh giá cost an toàn, xử lý MAX_DOUBLE (INF)
    is_best_inf = best.total_cost > 1e300
    is_trial_inf = trial.total_cost > 1e300

    best_cost_str = "INF (MAX_DOUBLE)" if is_best_inf else f"{best.total_cost:,.4f}"
    trial_cost_str = "INF (MAX_DOUBLE)" if is_trial_inf else f"{trial.total_cost:,.4f}"

    if is_best_inf and not is_trial_inf:
        verdict = "★ TRIAL WINS (Initial)"
    elif not is_trial_inf and not is_best_inf:
        cost_diff = trial.total_cost - best.total_cost
        if cost_diff < 0:
            verdict = f"★ TRIAL WINS ({cost_diff:-,.4f})"
        elif cost_diff > 0:
            verdict = f"Best Retained (+{cost_diff:,.4f})"
        else:
            verdict = "Equal Cost"
    else:
        verdict = "N/A"

    pred_mode_best = PRED_MODE_NAMES.get(best.pred_mode_list[0], "N/A") if best.pred_mode_list else "N/A"
    pred_mode_trial = PRED_MODE_NAMES.get(trial.pred_mode_list[0], "N/A") if trial.pred_mode_list else "N/A"

    part_size_best = PART_SIZE_NAMES.get(best.part_size_list[0], "N/A") if best.part_size_list else "N/A"
    part_size_trial = PART_SIZE_NAMES.get(trial.part_size_list[0], "N/A") if trial.part_size_list else "N/A"

    intra_best = intra_dir_to_str(best.intra_dir_luma_list[0]) if best.intra_dir_luma_list else "N/A"
    intra_trial = intra_dir_to_str(trial.intra_dir_luma_list[0]) if trial.intra_dir_luma_list else "N/A"

    dist_diff = trial.total_distortion - best.total_distortion
    bits_diff = trial.total_bits - best.total_bits

    dist_diff_str = f"+{dist_diff:,}" if dist_diff > 0 else f"{dist_diff:,}"
    bits_diff_str = f"+{bits_diff:,}" if bits_diff > 0 else f"{bits_diff:,}"

    rows = [
        sep,
        title,
        sep,
        f"{'Metric / Property':<22} | {'Current Best':<22} | {'Trial Candidate':<22} | {'Evaluation':<24}",
        "-" * 22 + "-+-" + "-" * 22 + "-+-" + "-" * 22 + "-+-" + "-" * 24,
        f"{'Prediction Mode':<22} | {pred_mode_best:<22} | {pred_mode_trial:<22} | {'Match' if pred_mode_best == pred_mode_trial else 'Changed':<24}",
        f"{'Partition Size':<22} | {part_size_best:<22} | {part_size_trial:<22} | {'Match' if part_size_best == part_size_trial else 'Changed':<24}",
        f"{'Luma Intra Dir':<22} | {intra_best:<22} | {intra_trial:<22} | {'Match' if intra_best == intra_trial else 'Changed':<24}",
        f"{'Distortion':<22} | {best.total_distortion:<22,} | {trial.total_distortion:<22,} | {dist_diff_str:<24}",
        f"{'Bits':<22} | {best.total_bits:<22,} | {trial.total_bits:<22,} | {bits_diff_str:<24}",
        f"{'Total RD-Cost':<22} | {best_cost_str:<22} | {trial_cost_str:<22} | {verdict:<24}",
        sep,
    ]

    return "\n".join(rows)
