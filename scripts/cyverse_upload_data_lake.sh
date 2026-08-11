#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-.env}"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  echo "Missing ${ENV_FILE}. Copy .env.example to .env and fill in CyVerse credentials." >&2
  exit 2
fi

export IRODS_HOST="${IRODS_HOST:-data.cyverse.org}"
export IRODS_PORT="${IRODS_PORT:-1247}"
export IRODS_ZONE_NAME="${IRODS_ZONE_NAME:-iplant}"

: "${IRODS_USER_NAME:?Set IRODS_USER_NAME in ${ENV_FILE}}"
: "${IRODS_USER_PASSWORD:?Set IRODS_USER_PASSWORD in ${ENV_FILE}}"

if [[ "${IRODS_USER_NAME}" == "your_cyverse_username" || "${IRODS_USER_PASSWORD}" == "your_cyverse_password_or_app_password" ]]; then
  echo "Edit ${ENV_FILE} and replace the placeholder CyVerse username/password before uploading." >&2
  exit 2
fi

GOCMD_BIN="${GOCMD_BIN:-${ROOT}/.tools/gocmd/gocmd}"
DATA_LAKE_PACKAGE="${DATA_LAKE_PACKAGE:-data_lake/fire-vase-data-lake-v0.1}"
CYVERSE_DEST="${CYVERSE_DEST:-/iplant/home/shared/esiil/Fire_Vase}"
THREAD_NUM="${GOCMD_THREAD_NUM:-5}"
THREAD_NUM_PER_FILE="${GOCMD_THREAD_NUM_PER_FILE:-2}"
REPORT="${GOCMD_REPORT:-${DATA_LAKE_PACKAGE}/cyverse_transfer_report.json}"

if [[ ! -x "${GOCMD_BIN}" ]]; then
  echo "gocmd not found at ${GOCMD_BIN}. Install it or set GOCMD_BIN." >&2
  exit 2
fi

if [[ ! -d "${DATA_LAKE_PACKAGE}" ]]; then
  echo "Missing data lake package: ${DATA_LAKE_PACKAGE}" >&2
  echo "Run: uv run python scripts/prepare_data_lake.py --mode hardlink --checksum" >&2
  exit 2
fi

echo "Using gocmd: ${GOCMD_BIN}"
echo "Source: ${DATA_LAKE_PACKAGE}"
echo "Destination: ${CYVERSE_DEST}"

"${GOCMD_BIN}" mkdir -p "${CYVERSE_DEST}"

"${GOCMD_BIN}" put \
  --progress \
  --show_path \
  --force \
  --diff \
  --verify_checksum \
  --retry 5 \
  --retry_interval 10 \
  --thread_num "${THREAD_NUM}" \
  --thread_num_per_file "${THREAD_NUM_PER_FILE}" \
  --report "${REPORT}" \
  "${DATA_LAKE_PACKAGE}" \
  "${CYVERSE_DEST}/"

echo "Transfer report: ${REPORT}"
