from __future__ import annotations

from uavtre.submit_v1.evidence_lock import run_evidence_lock


def test_evidence_lock_passes_when_all_files_exist(tmp_path):
    camp = tmp_path / "campaign"
    camp.mkdir()
    for name in ["CAMPAIGN_MANIFEST.json", "RUN_PLAN.json", "ENV_SNAPSHOT.json", "COMMAND_LOG.csv"]:
        (camp / name).write_text("{}", encoding="utf-8")

    report = tmp_path / "EVIDENCE_LOCK_REPORT.json"
    result = run_evidence_lock(camp, report)
    assert result.passed
    assert report.exists()


def test_evidence_lock_fails_on_missing_file(tmp_path):
    camp = tmp_path / "campaign"
    camp.mkdir()
    for name in ["CAMPAIGN_MANIFEST.json", "RUN_PLAN.json", "ENV_SNAPSHOT.json"]:
        (camp / name).write_text("{}", encoding="utf-8")

    report = tmp_path / "EVIDENCE_LOCK_REPORT.json"
    result = run_evidence_lock(camp, report)
    assert not result.passed
    assert "COMMAND_LOG.csv" in result.missing_files
