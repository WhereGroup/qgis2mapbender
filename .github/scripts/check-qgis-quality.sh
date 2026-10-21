#!/usr/bin/env bash

set -euo pipefail

PLUGIN_DIRECTORY="${1:?Plugin directory is required}"
QUALITY_CONFIG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/qgis-quality.env"

if [[ ! -f "${QUALITY_CONFIG}" ]]; then
  echo "Quality configuration not found: ${QUALITY_CONFIG}"
  exit 1
fi

# shellcheck disable=SC1090
source "${QUALITY_CONFIG}"

bandit --recursive "${PLUGIN_DIRECTORY}"

SECRETS_REPORT="$(mktemp)"
trap 'rm -f "${SECRETS_REPORT}"' EXIT

detect-secrets scan \
  --all-files \
  --exclude-files 'metadata\.txt' \
  --exclude-files '\.secrets\.baseline' \
  "${PLUGIN_DIRECTORY}" > "${SECRETS_REPORT}"

python - "${SECRETS_REPORT}" <<'PY'
import json
import sys

report_path = sys.argv[1]
with open(report_path, encoding="utf-8") as report_file:
    report = json.load(report_file)

findings = [
    (filename, finding)
    for filename, file_findings in report.get("results", {}).items()
    for finding in file_findings
]

if findings:
    for filename, finding in findings:
        line = finding.get("line_number", 0)
        detector = finding.get("type", "unknown detector")
        print(f"{filename}:{line}: {detector}", file=sys.stderr)
    raise SystemExit(f"{len(findings)} potential secret(s) detected.")
PY

set +e
flake8 \
  "${PLUGIN_DIRECTORY}" \
  --max-line-length="${QGIS_FLAKE8_MAX_LINE_LENGTH}" \
  --select="${QGIS_FLAKE8_SELECT}"
FLAKE8_STATUS=$?
set -e

if (( FLAKE8_STATUS > 1 )); then
  echo "Flake8 failed to run (exit code ${FLAKE8_STATUS})."
  exit "${FLAKE8_STATUS}"
fi

if (( FLAKE8_STATUS == 1 )); then
  echo "Flake8 reported advisory findings; the workflow continues."
fi
