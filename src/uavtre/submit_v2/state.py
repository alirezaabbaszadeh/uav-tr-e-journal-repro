from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class PipelineContext:
    root: Path
    campaign_id: str
    campaign_root: Path
    campaign_dir: Path
    run_id: str
    run_dir: Path
    state_path: Path
    logs_dir: Path
    out_submit_dir: Path
    out_manuscript_dir: Path


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def new_state(*, run_id: str, campaign_id: str, campaign_root: str, campaign_dir: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "campaign_id": campaign_id,
        "campaign_root": campaign_root,
        "campaign_dir": campaign_dir,
        "status": "initialized",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "current_step": "S00",
        "steps": {},
    }


def step_passed(state: dict[str, Any], step_id: str) -> bool:
    return state.get("steps", {}).get(step_id, {}).get("status") == "passed"


def start_step(state: dict[str, Any], step_id: str, description: str) -> None:
    steps = state.setdefault("steps", {})
    prev = steps.get(step_id, {})
    steps[step_id] = {
        **prev,
        "step_id": step_id,
        "description": description,
        "status": "running",
        "started_at": utc_now_iso(),
        "ended_at": None,
        "exit_code": None,
        "error": None,
        "artifacts": [],
    }
    state["current_step"] = step_id
    state["updated_at"] = utc_now_iso()


def end_step(
    state: dict[str, Any],
    step_id: str,
    *,
    status: str,
    exit_code: int,
    artifacts: list[str] | None = None,
    error: str | None = None,
) -> None:
    steps = state.setdefault("steps", {})
    row = steps.get(step_id, {"step_id": step_id})
    row.update(
        {
            "status": status,
            "ended_at": utc_now_iso(),
            "exit_code": int(exit_code),
            "error": error,
            "artifacts": artifacts or [],
        }
    )
    steps[step_id] = row
    state["updated_at"] = utc_now_iso()


def set_pipeline_status(state: dict[str, Any], status: str) -> None:
    state["status"] = status
    state["updated_at"] = utc_now_iso()
