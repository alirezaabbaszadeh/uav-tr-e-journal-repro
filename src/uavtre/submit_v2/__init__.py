"""submit_v2: journal-grade TR-E submission pipeline (campaign-locked, no rerun).

This namespace is intentionally isolated from submit_v1 to keep legacy flows stable.
"""

from __future__ import annotations

__all__ = [
    "orchestrator",
    "evidence_lock",
    "evidence_index",
    "claim_guard",
    "manuscript_writer",
    "manuscript_builder",
    "bundle_builder",
    "portal_pack_builder",
    "state",
]
