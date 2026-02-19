from __future__ import annotations

import zipfile

from uavtre.submit_v1.portal_pack_builder import check_pack


def test_pack_checker_detects_complete_pack(tmp_path):
    cid = "abc"
    pack = tmp_path / f"TR_E_UPLOAD_PACK_{cid}.zip"
    names = [
        "main.pdf",
        "source.zip",
        "proposal_highlights.txt",
        "cover_letter.txt",
        "TR_E_METADATA.yaml",
        f"TR_E_UPLOAD_CHECKLIST_{cid}.md",
        f"CLAIM_EVIDENCE_MAP_{cid}.md",
        f"TABLE_FIGURE_INDEX_{cid}.md",
        f"AUDIT_RECHECK_{cid}.json",
        f"MANUSCRIPT_EXEC_MANIFEST_{cid}.json",
        "SHA256SUMS.txt",
    ]
    with zipfile.ZipFile(pack, "w") as zf:
        for n in names:
            zf.writestr(n, "x")

    result = check_pack(pack, cid)
    assert result["passed"]


def test_pack_checker_fails_when_member_missing(tmp_path):
    cid = "abc"
    pack = tmp_path / f"TR_E_UPLOAD_PACK_{cid}.zip"
    with zipfile.ZipFile(pack, "w") as zf:
        zf.writestr("main.pdf", "x")

    result = check_pack(pack, cid)
    assert not result["passed"]
    assert f"CLAIM_EVIDENCE_MAP_{cid}.md" in result["missing"]
