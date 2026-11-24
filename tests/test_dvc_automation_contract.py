"""Regression contracts for selective, reviewed DVC automation.

These checks have no remote access and use only committed workflow sources.
Real-data integration is validated separately by the DVC Actions workflow.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "dvc-pipeline.yaml"
SCRIPT = ROOT / "scripts" / "verify_dvc_pipeline.sh"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_dvc_pipeline_has_no_schedule_or_unfiltered_push():
    workflow = _workflow()
    assert not re.search(r"(?m)^  schedule:\s*$", workflow)
    assert re.search(r"(?m)^  push:\s*\n    branches: \[main\]\s*\n    paths:", workflow)
    assert "src/hydrosight/eda/" not in workflow
    assert "src/hydrosight/features/" not in workflow


def test_automatic_dvc_runs_only_when_enabled():
    workflow = _workflow()
    assert "github.event_name == 'push' && vars.HYDROSIGHT_DVC_ENABLED == 'true'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "github.event_name == 'workflow_dispatch' && inputs.operation == 'validate'" in workflow


def test_dvc_publishing_requires_changed_metadata():
    workflow = _workflow()
    assert 'if git diff --quiet -- dvc.lock data/pipeline/.gitignore; then' in workflow
    assert 'echo "changed=false" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "changed=true" >> "$GITHUB_OUTPUT"' in workflow
    assert workflow.count("if: steps.dvc_changes.outputs.changed == 'true'") == 2
    assert "dvc push" in workflow
    assert "gh pr create" in workflow
    assert "gh pr merge" not in workflow


def test_validation_is_read_only_and_detects_dirty_lock():
    workflow = _workflow()
    validation = workflow.split("\n  validate:", 1)[1].split("\n  publish:", 1)[0]
    assert "git diff --quiet -- dvc.lock" in validation
    assert "dvc push" not in validation
    assert "gh pr create" not in validation
    assert "dvc status -c" in validation


def test_pipeline_recovers_missing_new_stage_outputs():
    script = _script()
    assert "dvc pull --allow-missing" in script
    assert script.index("dvc pull --allow-missing") < script.index("\ndvc repro")
    assert script.index("\ndvc repro") < script.index("PYTHONPATH=src python -m pytest -q")


def test_oauth_credentials_are_not_embedded_in_workflow():
    workflow = _workflow()
    script = _script()
    assert "secrets.HYDROSIGHT_GDRIVE_OAUTH_JSON" in workflow
    assert "secrets.HYDROSIGHT_GDRIVE_SERVICE_ACCOUNT_JSON" not in workflow
    assert "HYDROSIGHT_GDRIVE_OAUTH_JSON" in script
    assert "gdrive_use_service_account true" not in script
    assert "print(credentials)" not in script
