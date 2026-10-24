"""
gdb_scripts/core/session.py
----------------------------
Quản lý phiên gỡ lỗi HM-Debugger: Target POC, Target CTU, Committed Grid, và Candidate Counter.
"""

from typing import Any, Dict, List, Optional


class InspectorSession:
    """
    Singleton quản lý trạng thái phiên làm việc của GDB Inspector.
    """
    _instance: Optional["InspectorSession"] = None

    def __init__(self):
        self.target_poc: int = 0
        self.target_ctu: int = 0
        self.is_active: bool = False
        self.candidate_count: int = 0
        self.last_winner: str = "NONE"

        # Cache adapter tại breakpoint gần nhất
        self.current_trial = None
        self.current_best = None
        self.current_depth: int = 0

        # Committed Grid: Trạng thái chốt chính thức của 256 SCU 4x4 trong CTU 64x64
        self.committed_grid: List[Dict[str, Any]] = [
            {"depth": 0, "part_size": "N/A", "intra_dir": "N/A", "pred_mode": "N/A"}
            for _ in range(256)
        ]

    @classmethod
    def get_instance(cls) -> "InspectorSession":
        if cls._instance is None:
            cls._instance = InspectorSession()
        return cls._instance

    def reset(self, target_ctu: int = 0, target_poc: int = 0) -> None:
        """Đặt lại phiên với CTU và POC mục tiêu mới."""
        self.target_ctu = target_ctu
        self.target_poc = target_poc
        self.is_active = True
        self.candidate_count = 0
        self.last_winner = "NONE"
        self.current_trial = None
        self.current_best = None
        self.current_depth = 0
        self.committed_grid = [
            {"depth": 0, "part_size": "N/A", "intra_dir": "N/A", "pred_mode": "N/A"}
            for _ in range(256)
        ]

    def commit_cu_state(self, best_adapter) -> None:
        """
        Cập nhật kết quả chiến thắng cuối cùng của một CU vào Committed Grid.
        Chỉ được gọi tại Checkpoint xCopyYuv2Pic.
        """
        if not best_adapter or not best_adapter.is_valid:
            return

        for local_idx, abs_z_idx in best_adapter.get_partition_mappings():
            if 0 <= abs_z_idx < 256:
                d = best_adapter.depth_list[local_idx] if local_idx < len(best_adapter.depth_list) else 0
                ps = best_adapter.part_size_list[local_idx] if local_idx < len(best_adapter.part_size_list) else 0
                it = best_adapter.intra_dir_luma_list[local_idx] if local_idx < len(best_adapter.intra_dir_luma_list) else 0
                pm = best_adapter.pred_mode_list[local_idx] if local_idx < len(best_adapter.pred_mode_list) else 0

                self.committed_grid[abs_z_idx] = {
                    "depth": d,
                    "part_size": ps,
                    "intra_dir": it,
                    "pred_mode": pm,
                }
