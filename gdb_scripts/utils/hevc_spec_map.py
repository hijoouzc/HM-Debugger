"""
gdb_scripts/utils/hevc_spec_map.py
----------------------------------
Centralized ITU-T H.265 (ISO/IEC 23008-2) Semantic Registry & Selective Decorator
for HM-18.0 Reference Software.

Nomenclature Policy:
1. HM Code-First: The C++ variable name is always the primary identifier.
2. Enum Parity: Preserves exact C++ enum symbols (e.g. SIZE_2Nx2N, MODE_INTRA).
3. Selective Dual-Display: Only attaches H.265 syntax tags to cryptic abbreviations.
4. Language: Strictly technical English per ITU-T H.265 specification.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class HEVCSyntaxTag:
    """Represents an ITU-T H.265 standard syntax mapping definition."""
    tag: str           # Short bracketed tag, e.g. "[part_mode]"
    spec_name: str     # H.265 standard syntax element name
    clause: str        # H.265 specification clause reference
    description: str   # Standard English definition


# Explicit mapping curated strictly for cryptic or abbreviated HM member variables
SELECTIVE_SPEC_TAGS: Dict[str, HEVCSyntaxTag] = {
    "m_pePartSize": HEVCSyntaxTag(
        tag="[part_mode]",
        spec_name="part_mode",
        clause="Table 7-10 / Clause 7.3.8.5",
        description="CU partitioning mode (SIZE_2Nx2N, SIZE_2NxN, SIZE_Nx2N, SIZE_NxN)"
    ),
    "m_pePredMode": HEVCSyntaxTag(
        tag="[pred_mode_flag]",
        spec_name="pred_mode_flag",
        clause="Table 7-11 / Clause 7.3.8.5",
        description="CU prediction mode (MODE_INTRA, MODE_INTER)"
    ),
    "m_puhCbf": HEVCSyntaxTag(
        tag="[cbf: Y/Cb/Cr]",
        spec_name="cbf_luma, cbf_cb, cbf_cr",
        clause="Clause 7.3.8.8",
        description="Coded block flags for Y, Cb, Cr transform blocks"
    ),
    "m_puhTrIdx": HEVCSyntaxTag(
        tag="[transform_depth]",
        spec_name="transform_depth",
        clause="Clause 7.3.8.8",
        description="Transform quadtree subdivision depth"
    ),
    "m_puhIntraDir": HEVCSyntaxTag(
        tag="[intra_pred_mode]",
        spec_name="intra_luma_pred_mode / intra_chroma_pred_mode",
        clause="Table 8-2 / Clause 8.4.2",
        description="Intra prediction angular direction"
    ),
    "m_acCUMvField": HEVCSyntaxTag(
        tag="[MV List 0/1]",
        spec_name="mvd_coding",
        clause="Clause 7.3.8.6",
        description="Motion vector fields for Reference List 0 and List 1"
    ),
}


def get_selective_tag(var_name: str) -> Optional[HEVCSyntaxTag]:
    """Retrieve the H.265 specification tag if the variable is cryptic; returns None otherwise."""
    return SELECTIVE_SPEC_TAGS.get(var_name)


def format_member_label(var_name: str) -> str:
    """
    Format a member variable label.
    If the variable is in the selective registry, appends the H.265 tag:
      e.g. "m_pePartSize [part_mode]"
    Otherwise, returns the unchanged C++ variable name:
      e.g. "m_puhDepth"
    """
    tag_info = SELECTIVE_SPEC_TAGS.get(var_name)
    if tag_info:
        return f"{var_name} {tag_info.tag}"
    return var_name
