from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _replace_todo_tokens(text: str) -> str:
    replacements = {
        "TODO_TITLE": "Reliability-Aware Multi-UAV Pickup and Delivery under Communication Risk",
        "TODO_RUNNING_TITLE": "Reliability-Aware Multi-UAV Logistics",
        "TODO_ABSTRACT": "Campaign-locked reproducible study for reliability-aware multi-UAV pickup and delivery.",
        "TODO_KEYWORDS": "UAV logistics; VRPTW; communication risk; reproducibility",
        "TODO_AUTHORS": "Corresponding Author",
        "TODO_CORRESPONDING_AUTHOR": "Corresponding Author",
        "TODO_AFFILIATIONS": "Independent Researcher",
        "TODO_FUNDING": "No external funding",
        "TODO_CONFLICTS": "The authors declare no conflict of interest.",
        "TODO_DATA_CODE_AVAILABILITY": "Code and artifacts are available in the companion repository.",
    }

    def repl(match: re.Match[str]) -> str:
        key = match.group(0)
        return replacements.get(key, "AUTO_FILLED")

    return re.sub(r"TODO_[A-Z0-9_]+", repl, text)


def materialize_metadata(template_path: Path, metadata_path: Path) -> Path:
    template_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    if metadata_path.exists():
        text = metadata_path.read_text(encoding="utf-8")
        if "TODO_" not in text:
            return metadata_path

    template_text = template_path.read_text(encoding="utf-8")
    metadata = _replace_todo_tokens(template_text)
    if "TODO_" in metadata:
        raise RuntimeError("metadata still contains TODO placeholders")
    metadata_path.write_text(metadata, encoding="utf-8")
    return metadata_path


def build_source_zip(manuscript_root: Path, out_submission_dir: Path, campaign_id: str) -> Path:
    source_zip = out_submission_dir / f"source_{campaign_id}.zip"
    with zipfile.ZipFile(source_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(manuscript_root.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(manuscript_root.parent)))
    return source_zip


def build_tr_e_upload_pack(
    *,
    campaign_id: str,
    out_submission_dir: Path,
    out_manuscript_dir: Path,
    manuscript_root: Path,
    audit_recheck_json: Path,
    manifest_json: Path,
) -> Path:
    out_submission_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = out_manuscript_dir / "main.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    template_path = out_submission_dir / "TR_E_METADATA_TEMPLATE.yaml"
    metadata_path = out_submission_dir / "TR_E_METADATA.yaml"
    materialize_metadata(template_path, metadata_path)

    source_zip = build_source_zip(manuscript_root, out_submission_dir, campaign_id)

    required_files = {
        "main.pdf": pdf_path,
        "source.zip": source_zip,
        "proposal_highlights.txt": out_submission_dir / "proposal_highlights.txt",
        "cover_letter.txt": out_submission_dir / "cover_letter.txt",
        "TR_E_METADATA.yaml": metadata_path,
        f"TR_E_UPLOAD_CHECKLIST_{campaign_id}.md": out_submission_dir / f"TR_E_UPLOAD_CHECKLIST_{campaign_id}.md",
        f"CLAIM_EVIDENCE_MAP_{campaign_id}.md": out_submission_dir / f"CLAIM_EVIDENCE_MAP_{campaign_id}.md",
        f"TABLE_FIGURE_INDEX_{campaign_id}.md": out_submission_dir / f"TABLE_FIGURE_INDEX_{campaign_id}.md",
        f"AUDIT_RECHECK_{campaign_id}.json": audit_recheck_json,
        f"MANUSCRIPT_EXEC_MANIFEST_{campaign_id}.json": manifest_json,
    }

    missing = [name for name, path in required_files.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required upload files: {missing}")

    checksums_path = out_submission_dir / "SHA256SUMS.txt"
    checksum_lines = [f"{_sha256(path)}  {name}" for name, path in required_files.items()]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    required_files["SHA256SUMS.txt"] = checksums_path

    pack_path = out_submission_dir / f"TR_E_UPLOAD_PACK_{campaign_id}.zip"
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, src in required_files.items():
            zf.write(src, arcname=arcname)

    return pack_path


def check_pack(pack_path: Path, campaign_id: str) -> dict[str, object]:
    required = {
        "main.pdf",
        "source.zip",
        "proposal_highlights.txt",
        "cover_letter.txt",
        "TR_E_METADATA.yaml",
        f"TR_E_UPLOAD_CHECKLIST_{campaign_id}.md",
        f"CLAIM_EVIDENCE_MAP_{campaign_id}.md",
        f"TABLE_FIGURE_INDEX_{campaign_id}.md",
        f"AUDIT_RECHECK_{campaign_id}.json",
        f"MANUSCRIPT_EXEC_MANIFEST_{campaign_id}.json",
        "SHA256SUMS.txt",
    }

    if not pack_path.exists():
        return {
            "pack": pack_path.as_posix(),
            "exists": False,
            "missing": sorted(required),
            "passed": False,
        }

    with zipfile.ZipFile(pack_path, "r") as zf:
        names = set(zf.namelist())

    missing = sorted(required - names)
    return {
        "pack": pack_path.as_posix(),
        "exists": True,
        "member_count": len(names),
        "missing": missing,
        "passed": len(missing) == 0,
    }
