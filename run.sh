#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
REQUIREMENTS_FILE="${ROOT_DIR}/requirements.txt"
STAMP_FILE="${VENV_DIR}/.requirements.stamp"

cd "${ROOT_DIR}"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d "${VENV_DIR}" ]]; then
        python3 -m venv "${VENV_DIR}"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
fi

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    echo "Missing ${REQUIREMENTS_FILE}" >&2
    exit 1
fi

CURRENT_STAMP="$(sha256sum "${REQUIREMENTS_FILE}" | awk '{print $1}')"
INSTALLED_STAMP=""

if [[ -f "${STAMP_FILE}" ]]; then
    INSTALLED_STAMP="$(<"${STAMP_FILE}")"
fi

if [[ "${CURRENT_STAMP}" != "${INSTALLED_STAMP}" ]]; then
    python -m pip install --upgrade pip
    python -m pip install -r "${REQUIREMENTS_FILE}"
    printf '%s\n' "${CURRENT_STAMP}" > "${STAMP_FILE}"
fi

exec python SongFormatter.py "$@"
