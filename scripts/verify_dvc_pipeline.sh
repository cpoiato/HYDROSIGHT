#!/usr/bin/env bash
# Validate the committed real-data pipeline. Never download synthetic production data.
set -euo pipefail

if [[ ! -f dvc.yaml || ! -f .dvc/config ]]; then
  echo "Run this script from the HYDROSIGHT repository root." >&2
  exit 1
fi

# CI uses the existing DVC-compatible user OAuth credentials; local execution
# uses the operator's existing DVC OAuth profile. Do not print or persist secrets.
mode="${1:-validate}"
if [[ "$mode" != "validate" && "$mode" != "publish" ]]; then
  echo "Usage: bash scripts/verify_dvc_pipeline.sh [validate|publish]" >&2
  exit 2
fi

if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  python - <<'PY'
import json
import os

raw = os.environ.get("GDRIVE_CREDENTIALS_DATA", "")
if not raw:
    raise SystemExit("Missing GitHub secret HYDROSIGHT_GDRIVE_OAUTH_JSON")
try:
    credentials = json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit("Google Drive OAuth secret is not valid JSON") from exc
if not isinstance(credentials, dict) or not all(
    credentials.get(field) for field in ("client_id", "client_secret", "refresh_token")
):
    raise SystemExit("Google Drive OAuth credentials lack client_id, client_secret or refresh_token")
if credentials.get("type") == "service_account":
    raise SystemExit("Expected the DVC OAuth profile, not a service-account key")
PY
fi

# A new pipeline stage may have no published output yet; fetch existing snapshots
# but let DVC regenerate only genuinely missing/changed derived stages.
dvc pull --allow-missing
dvc repro
PYTHONPATH=src python -m pytest -q

python - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("data/processed/spatial_grid_manifest.json").read_text(encoding="utf-8"))
quality = json.loads(Path("data/pipeline/break_history/break_history_quality.json").read_text(encoding="utf-8"))
if manifest["grid_size_meters"] != 500:
    raise SystemExit("Only the approved 500 m spatial grid can be used")
if quality["grid_version"] != manifest["active_version"]:
    raise SystemExit("Break history was built against a different grid version")
if quality["grid_cells"] != manifest["cell_count"]:
    raise SystemExit("Break history grid size does not match the active grid")
if quality["source_records"] != quality["assigned_records"] + quality["unassigned_records"]:
    raise SystemExit("Observed water-break counts do not reconcile")
if not Path("data/pipeline/break_history/breaks_by_sector_month.csv").is_file():
    raise SystemExit("Observed break history CSV was not produced")
print("PASS: real-data DVC history and spatial-grid consistency")
PY

dvc status

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  python - <<'PY' >> "$GITHUB_STEP_SUMMARY"
import json
from pathlib import Path

quality = json.loads(Path("data/pipeline/break_history/break_history_quality.json").read_text(encoding="utf-8"))
print("### Real-data pipeline validation")
print("\n| Metric | Value |\n|---|---:|")
for key in ("grid_version", "grid_cells", "source_records", "assigned_records", "unassigned_records", "border_ties_resolved", "sector_month_records"):
    print(f"| {key} | {quality[key]} |")
print("\nDataset: official Calgary source snapshots already committed in DVC metadata. No new source extraction was performed.")
PY
fi
