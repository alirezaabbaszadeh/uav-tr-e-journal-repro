from __future__ import annotations

import json
import re
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .bundle_builder import build_bundles
from .claim_guard import validate_claims, write_claim_registry_yaml
from .evidence_index import build_evidence_index
from .evidence_lock import run_evidence_lock
from .manuscript_builder import compile_manuscript, generate_assets
from .manuscript_writer import materialize_campaign_lock, write_submission_text_artifacts
from .portal_pack_builder import build_tr_e_upload_pack, check_pack
from .state import (
    PipelineContext,
    end_step,
    load_state,
    new_state,
    set_pipeline_status,
    sha256_file,
    start_step,
    step_passed,
    utc_now_iso,
    write_state,
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _resolve_campaign_dir(root: Path, campaign_root: str, campaign_id: str) -> Path:
    base = Path(campaign_root)
    if not base.is_absolute():
        base = root / base

    # Allow passing either the campaigns root or an explicit campaign directory.
    if base.name == campaign_id and base.exists():
        return base
    return base / campaign_id


def _discover_resume_run(root: Path, campaign_id: str) -> str | None:
    runs_root = root / "outputs" / "pipeline_v2_runs"
    if not runs_root.exists():
        return None
    candidates: list[tuple[float, str]] = []
    for path in runs_root.iterdir():
        if not path.is_dir():
            continue
        state_path = path / "STATE.json"
        if not state_path.exists():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if state.get("campaign_id") != campaign_id:
            continue
        if state.get("status") in {"ready_for_portal_submit", "completed"}:
            continue
        candidates.append((path.stat().st_mtime, path.name))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def _run_subprocess(cmd: list[str], *, cwd: Path, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    log_text = "COMMAND: " + " ".join(cmd) + "\n\n" + (proc.stdout or "") + "\n" + (proc.stderr or "")
    log_path.write_text(log_text, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"command failed with exit {proc.returncode}: {' '.join(cmd)}")


def _ensure_metadata_template(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "title: TODO_TITLE\n"
        "running_title: TODO_RUNNING_TITLE\n"
        "abstract: TODO_ABSTRACT\n"
        "keywords: TODO_KEYWORDS\n"
        "authors: TODO_AUTHORS\n"
        "corresponding_author: TODO_CORRESPONDING_AUTHOR\n"
        "affiliations: TODO_AFFILIATIONS\n"
        "funding: TODO_FUNDING\n"
        "conflicts: TODO_CONFLICTS\n"
        "data_code_availability: TODO_DATA_CODE_AVAILABILITY\n",
        encoding="utf-8",
    )


def _write_exec_manifest(
    *,
    ctx: PipelineContext,
    state: dict,
    audit_path: Path,
    final_status: str,
    pack_path: Path | None,
) -> Path:
    out_path = ctx.out_submit_dir / f"MANUSCRIPT_EXEC_MANIFEST_{ctx.campaign_id}.json"

    artifact_paths: list[Path] = [
        ctx.out_manuscript_dir / "anonymous" / "main.pdf",
        ctx.out_manuscript_dir / "camera_ready" / "main.pdf",
        ctx.out_submit_dir / f"CLAIM_EVIDENCE_MAP_{ctx.campaign_id}.md",
        ctx.out_submit_dir / f"TABLE_FIGURE_INDEX_{ctx.campaign_id}.md",
        ctx.out_submit_dir / f"TR_E_UPLOAD_CHECKLIST_{ctx.campaign_id}.md",
        ctx.out_submit_dir / f"AUDIT_RECHECK_{ctx.campaign_id}.json",
        ctx.out_submit_dir / f"CLAIM_GUARD_REPORT_{ctx.campaign_id}.json",
        ctx.out_submit_dir / f"EVIDENCE_INDEX_{ctx.campaign_id}.csv",
        ctx.out_submit_dir / "TR_E_METADATA.yaml",
    ]
    if pack_path is not None:
        artifact_paths.append(pack_path)

    artifacts = []
    for path in artifact_paths:
        if not path.exists():
            continue
        artifacts.append(
            {
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )

    payload = {
        "generated_at_utc": utc_now_iso(),
        "run_id": ctx.run_id,
        "campaign_id": ctx.campaign_id,
        "campaign_root": ctx.campaign_root.as_posix(),
        "campaign_dir": ctx.campaign_dir.as_posix(),
        "git_sha": _read_git_sha(ctx.root),
        "audit_json": audit_path.as_posix(),
        "state_status": state.get("status"),
        "final_status": final_status,
        "pack_path": None if pack_path is None else pack_path.as_posix(),
        "artifacts": artifacts,
        "steps": state.get("steps", {}),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _read_git_sha(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "nogit-submit-v2"
    return (proc.stdout or "").strip() or "nogit-submit-v2"


def run_pipeline(
    *,
    root: Path,
    campaign_id: str,
    campaign_root: str,
    mode: str,
    resume: bool,
    run_id: str | None,
) -> PipelineContext:
    campaign_dir = _resolve_campaign_dir(root, campaign_root, campaign_id)
    if not campaign_dir.exists():
        raise FileNotFoundError(f"campaign not found: {campaign_dir}")

    runs_root = root / "outputs" / "pipeline_v2_runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    selected_run_id = run_id
    if resume and not selected_run_id:
        selected_run_id = _discover_resume_run(root, campaign_id)
    if not selected_run_id:
        selected_run_id = f"submit_v2_{campaign_id}_{_ts()}"

    run_dir = runs_root / selected_run_id
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    state_path = run_dir / "STATE.json"
    state = load_state(state_path)
    if not state:
        state = new_state(
            run_id=selected_run_id,
            campaign_id=campaign_id,
            campaign_root=Path(campaign_root).as_posix(),
            campaign_dir=campaign_dir.as_posix(),
        )
        write_state(state_path, state)

    ctx = PipelineContext(
        root=root,
        campaign_id=campaign_id,
        campaign_root=Path(campaign_root),
        campaign_dir=campaign_dir,
        run_id=selected_run_id,
        run_dir=run_dir,
        state_path=state_path,
        logs_dir=logs_dir,
        out_submit_dir=root / "output_submit_v2" / "submission",
        out_manuscript_dir=root / "output_submit_v2" / "manuscript",
    )
    ctx.out_submit_dir.mkdir(parents=True, exist_ok=True)
    ctx.out_manuscript_dir.mkdir(parents=True, exist_ok=True)

    _ensure_metadata_template(ctx.out_submit_dir / "TR_E_METADATA_TEMPLATE.yaml")

    evidence_lock_path = ctx.out_submit_dir / f"EVIDENCE_LOCK_REPORT_{campaign_id}.json"
    audit_path = ctx.out_submit_dir / f"AUDIT_RECHECK_{campaign_id}.json"
    evidence_csv = ctx.out_submit_dir / f"EVIDENCE_INDEX_{campaign_id}.csv"
    claim_yaml = ctx.out_submit_dir / f"CLAIM_REGISTRY_{campaign_id}.yaml"
    claim_report = ctx.out_submit_dir / f"CLAIM_GUARD_REPORT_{campaign_id}.json"
    final_qa = ctx.out_submit_dir / f"FINAL_QA_REPORT_{campaign_id}.json"

    manuscript_root = root / "manuscript_submit_v2" / "tr_e"

    def s01() -> list[str]:
        res = run_evidence_lock(ctx.campaign_dir, evidence_lock_path)
        if not res.passed:
            raise RuntimeError(f"evidence lock failed: missing {res.missing_files}")
        return [evidence_lock_path.as_posix()]

    def s02() -> list[str]:
        cmd = [
            "python3",
            "scripts/audit_journal_readiness.py",
            "--campaign-id",
            campaign_id,
            "--campaign-root",
            "outputs/campaigns",
            "--json-out",
            audit_path.as_posix(),
            "--fail-on-critical",
            "--fail-on-high",
        ]
        _run_subprocess(cmd, cwd=root, log_path=ctx.logs_dir / "S02_audit.log")
        return [audit_path.as_posix(), (ctx.logs_dir / "S02_audit.log").as_posix()]

    def s03() -> list[str]:
        build_evidence_index(
            campaign_dir=ctx.campaign_dir,
            campaign_id=campaign_id,
            out_csv=evidence_csv,
            audit_json=audit_path,
        )
        return [evidence_csv.as_posix()]

    def s04() -> list[str]:
        write_claim_registry_yaml(campaign_id, claim_yaml)
        return [claim_yaml.as_posix()]

    def s05() -> list[str]:
        res = validate_claims(
            campaign_id=campaign_id,
            evidence_csv=evidence_csv,
            claim_registry_yaml=claim_yaml,
            report_path=claim_report,
            manuscript_root=manuscript_root,
        )
        if not res.passed:
            raise RuntimeError(
                f"claim guard failed: unresolved={res.unresolved} "
                f"violations={res.policy_violations} evid_missing={res.evidence_tag_missing}"
            )
        return [claim_report.as_posix()]

    def s06() -> list[str]:
        written = generate_assets(
            campaign_dir=ctx.campaign_dir,
            manuscript_root=manuscript_root,
        )
        return [p.as_posix() for p in written]

    def s07() -> list[str]:
        lock_path = materialize_campaign_lock(
            campaign_id=campaign_id,
            campaign_dir=ctx.campaign_dir,
            out_path=manuscript_root / "generated" / "campaign_lock.tex",
        )
        return [lock_path.as_posix()]

    def s08() -> list[str]:
        out = []
        out.append(
            compile_manuscript(
                root=root,
                manuscript_root=manuscript_root,
                outdir=ctx.out_manuscript_dir / "anonymous",
                variant="anonymous",
            ).as_posix()
        )
        out.append(
            compile_manuscript(
                root=root,
                manuscript_root=manuscript_root,
                outdir=ctx.out_manuscript_dir / "camera_ready",
                variant="camera_ready",
            ).as_posix()
        )
        return out

    def s09() -> list[str]:
        written = write_submission_text_artifacts(
            campaign_id=campaign_id,
            campaign_dir=ctx.campaign_dir,
            evidence_csv=evidence_csv,
            claim_report_json=claim_report,
            out_submission_dir=ctx.out_submit_dir,
        )
        return [p.as_posix() for p in written]

    def s10() -> list[str]:
        written = build_bundles(
            root=root,
            campaign_dir=ctx.campaign_dir,
            campaign_id=campaign_id,
            out_submission_dir=ctx.out_submit_dir,
            bundles_root=root / "submission_submit_v2",
            bundle_mode="both",
        )
        return [p.as_posix() for p in written]

    def s11() -> list[str]:
        # Provisional manifest required by pack contract.
        manifest_path = _write_exec_manifest(
            ctx=ctx,
            state=state,
            audit_path=audit_path,
            final_status="pre_pack",
            pack_path=None,
        )

        pack = build_tr_e_upload_pack(
            campaign_id=campaign_id,
            out_submission_dir=ctx.out_submit_dir,
            out_manuscript_dir=ctx.out_manuscript_dir,
            manuscript_root=manuscript_root,
            audit_recheck_json=audit_path,
            manifest_json=manifest_path,
            pdf_variant="camera_ready",
        )
        return [pack.as_posix()]

    def s12() -> list[str]:
        pack_path = ctx.out_submit_dir / f"TR_E_UPLOAD_PACK_{campaign_id}.zip"
        check = check_pack(pack_path, campaign_id)

        anon_manifest_path = root / "submission_submit_v2" / "anonymous" / "BUNDLE_MANIFEST.json"
        cam_manifest_path = root / "submission_submit_v2" / "camera_ready" / "BUNDLE_MANIFEST.json"

        anon_manifest = json.loads(anon_manifest_path.read_text(encoding="utf-8"))
        cam_manifest = json.loads(cam_manifest_path.read_text(encoding="utf-8"))

        metadata = (ctx.out_submit_dir / "TR_E_METADATA.yaml").read_text(encoding="utf-8")
        todo_left = "TODO_" in metadata

        # Manuscript quality gates (LaTeX + bibliography + required assets).
        log_path = ctx.out_manuscript_dir / "camera_ready" / "main.log"
        overfull_free = False
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="ignore")
            overfull_free = "Overfull \\hbox" not in log_text

        bbl_path = ctx.out_manuscript_dir / "camera_ready" / "main.bbl"
        bib_count = None
        bib_count_ok = False
        if bbl_path.exists():
            bbl = bbl_path.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"\\begin\{thebibliography\}\{(\d+)\}", bbl)
            if m:
                try:
                    bib_count = int(m.group(1))
                    bib_count_ok = bib_count >= 45
                except Exception:
                    bib_count_ok = False

        required_tables = [
            manuscript_root / "generated" / "tables" / "tab_comm_params.tex",
            manuscript_root / "generated" / "tables" / "tab_tw_families.tex",
            manuscript_root / "generated" / "tables" / "tab_significance_summary.tex",
        ]
        required_tables_present = all(t.exists() for t in required_tables)

        report = {
            "generated_at_utc": utc_now_iso(),
            "campaign_id": campaign_id,
            "checks": {
                "claim_guard_passed": json.loads(claim_report.read_text(encoding="utf-8")).get(
                    "passed", False
                ),
                "audit_recheck_exists": audit_path.exists(),
                "manuscript_pdf_exists": (ctx.out_manuscript_dir / "camera_ready" / "main.pdf").exists(),
                "anonymous_bundle_passed": bool(anon_manifest.get("passed", False)),
                "camera_ready_bundle_exists": cam_manifest_path.exists(),
                "pack_passed": bool(check.get("passed", False)),
                "metadata_todo_free": not todo_left,
                "latex_overfull_free": bool(overfull_free),
                "bibliography_count_ge_45": bool(bib_count_ok),
                "required_tables_present": bool(required_tables_present),
            },
            "pack_check": check,
            "latex": {"overfull_free": overfull_free},
            "bibliography": {"count": bib_count, "min_required": 45},
            "assets": {"required_tables": [p.as_posix() for p in required_tables]},
        }
        passed = all(bool(v) for v in report["checks"].values())
        report["passed"] = passed
        final_qa.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not passed:
            raise RuntimeError(f"final QA failed: {report['checks']}")
        return [final_qa.as_posix()]

    def s13() -> list[str]:
        metadata = (ctx.out_submit_dir / "TR_E_METADATA.yaml").read_text(encoding="utf-8")
        if "TODO_" in metadata:
            raise RuntimeError("TR_E_METADATA.yaml still contains TODO placeholders")

        pack_path = ctx.out_submit_dir / f"TR_E_UPLOAD_PACK_{campaign_id}.zip"
        final_manifest = _write_exec_manifest(
            ctx=ctx,
            state=state,
            audit_path=audit_path,
            final_status="ready_for_portal_submit",
            pack_path=pack_path,
        )
        return [final_manifest.as_posix()]

    steps: list[tuple[str, str, Callable[[], list[str]]]] = [
        ("S01", "Evidence freeze lock", s01),
        ("S02", "Hard scientific gate", s02),
        ("S03", "Build evidence index", s03),
        ("S04", "Build claim registry", s04),
        ("S05", "Claim guard validation", s05),
        ("S06", "Generate manuscript assets", s06),
        ("S07", "Materialize campaign lock for manuscript", s07),
        ("S08", "Compile manuscript PDFs (anonymous + camera-ready)", s08),
        ("S09", "Build submission text artifacts", s09),
        ("S10", "Build reviewer bundles", s10),
        ("S11", "Build TR-E upload pack", s11),
        ("S12", "Final consistency sweep", s12),
        ("S13", "Ready-to-submit status", s13),
    ]

    set_pipeline_status(state, "running")
    write_state(state_path, state)

    for step_id, description, fn in steps:
        if resume and step_passed(state, step_id):
            continue

        start_step(state, step_id, description)
        write_state(state_path, state)

        try:
            artifacts = fn()
            end_step(state, step_id, status="passed", exit_code=0, artifacts=artifacts)
            write_state(state_path, state)
        except Exception as exc:
            err = f"{exc}\n{traceback.format_exc()}"
            end_step(state, step_id, status="failed", exit_code=1, artifacts=[], error=err)
            set_pipeline_status(state, "failed")
            write_state(state_path, state)
            raise

    set_pipeline_status(state, "ready_for_portal_submit")
    state["completed_at"] = utc_now_iso()
    write_state(state_path, state)

    return ctx
