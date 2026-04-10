#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
HOOK_TARGET="${REPO_ROOT}/scripts/pre-commit.sh"
HOOK_PATH="$(git -C "${REPO_ROOT}" rev-parse --git-path hooks/pre-commit)"

if [[ "${HOOK_PATH}" != /* ]]; then
  HOOK_PATH="${REPO_ROOT}/${HOOK_PATH}"
fi

mkdir -p "$(dirname "${HOOK_PATH}")"

if [[ ! -e "${HOOK_TARGET}" ]]; then
  printf 'install-hooks: missing hook target %s\n' "${HOOK_TARGET}" >&2
  exit 1
fi

if [[ -e "${HOOK_PATH}" && ! -L "${HOOK_PATH}" ]]; then
  printf 'install-hooks: refusing to replace existing non-symlink hook at %s\n' "${HOOK_PATH}" >&2
  exit 1
fi

ln -sfn "${HOOK_TARGET}" "${HOOK_PATH}"
printf 'install-hooks: linked %s -> %s\n' "${HOOK_PATH}" "${HOOK_TARGET}"
