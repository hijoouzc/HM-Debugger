import sys
import os
sys.path.insert(0, os.path.abspath("."))

from gdb_scripts.inspector import GenericObjectInspector, DiffStatus

def test_diff_snapshots():
    snap_a = {
        "name": "cu",
        "category": "STRUCT",
        "value": {
            "m_dTotalCost": {"name": "m_dTotalCost", "category": "SCALAR", "value": 1500.0},
            "m_absZIdxInCtu": {"name": "m_absZIdxInCtu", "category": "SCALAR", "value": 0},
            "m_pePartSize": {"name": "m_pePartSize", "category": "POINTER", "value": "0x1234"},
        }
    }

    snap_b = {
        "name": "cu",
        "category": "STRUCT",
        "value": {
            "m_dTotalCost": {"name": "m_dTotalCost", "category": "SCALAR", "value": 1420.5},
            "m_absZIdxInCtu": {"name": "m_absZIdxInCtu", "category": "SCALAR", "value": 0},
            "m_pePartSize": {"name": "m_pePartSize", "category": "POINTER", "value": "0x1234"},
        }
    }

    diffs = GenericObjectInspector.diff_snapshots(snap_a, snap_b)
    diff_map = {d.path: d for d in diffs}

    assert diff_map["m_dTotalCost"].status == DiffStatus.CHANGED
    assert diff_map["m_dTotalCost"].val_a == 1500.0
    assert diff_map["m_dTotalCost"].val_b == 1420.5
    assert diff_map["m_absZIdxInCtu"].status == DiffStatus.MATCH
    assert diff_map["m_pePartSize"].status == DiffStatus.MATCH

    # Test TypeCategory enum
    from gdb_scripts.inspector import TypeCategory
    assert TypeCategory.CLASS == "CLASS"
    assert TypeCategory.STRUCT == "STRUCT"

    print("test_diff_snapshots: PASSED")

if __name__ == "__main__":
    test_diff_snapshots()
