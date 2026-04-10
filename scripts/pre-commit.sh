#!/usr/bin/env bash
set -euo pipefail

HOOK_NAME="heru pre-commit"
SMOKE_TESTS=(
  "tests/test_runner_workflow.py"
  "tests/test_engine_variants_and_timeline.py"
  "tests/test_heru_cli.py"
  "tests/test_codex_quota.py"
  "tests/test_observability_and_status.py"
)

say() {
  printf '%s\n' "$*" >&2
}

resolve_abs_path() {
  local path="$1"

  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "$(pwd -P)/$path"
  fi
}

discover_litehive_repo() {
  local sibling_candidate="$1"

  if [[ -d "$sibling_candidate" ]]; then
    printf '%s\n' "$sibling_candidate"
    return 0
  fi

  if [[ -n "${LITEHIVE_REPO:-}" && -d "${LITEHIVE_REPO}" ]]; then
    printf '%s\n' "$(cd "${LITEHIVE_REPO}" && pwd -P)"
    return 0
  fi

  return 1
}

remove_untracked_files() {
  if [[ ! -s "${SAVED_STATE_DIR}/untracked.list" ]]; then
    return 0
  fi

  xargs -0 rm -rf -- <"${SAVED_STATE_DIR}/untracked.list"
}

save_unstaged_state() {
  SAVED_STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/heru-pre-commit.XXXXXX")"
  git diff --binary -- >"${SAVED_STATE_DIR}/unstaged.patch"
  git ls-files --others --exclude-standard -z >"${SAVED_STATE_DIR}/untracked.list"

  if [[ -s "${SAVED_STATE_DIR}/untracked.list" ]]; then
    tar -cf "${SAVED_STATE_DIR}/untracked.tar" --null -T "${SAVED_STATE_DIR}/untracked.list"
  fi

  git checkout-index --all --force
  remove_untracked_files
}

restore_unstaged_state() {
  if [[ -z "${SAVED_STATE_DIR:-}" ]]; then
    return 0
  fi

  local restore_failed=0

  if [[ -f "${SAVED_STATE_DIR}/untracked.tar" ]]; then
    tar -xf "${SAVED_STATE_DIR}/untracked.tar"
  fi

  if [[ -s "${SAVED_STATE_DIR}/unstaged.patch" ]] && ! git apply --binary "${SAVED_STATE_DIR}/unstaged.patch"; then
    say "${HOOK_NAME}: failed to restore unstaged tracked changes."
    say "${HOOK_NAME}: patch preserved at ${SAVED_STATE_DIR}/unstaged.patch"
    restore_failed=1
  fi

  if [[ "${restore_failed}" -eq 0 ]]; then
    rm -rf "${SAVED_STATE_DIR}"
  fi

  return "${restore_failed}"
}

cleanup() {
  local status=$?

  if ! restore_unstaged_state; then
    status=1
  fi

  exit "${status}"
}

trap cleanup EXIT

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${repo_root}" ]]; then
  say "${HOOK_NAME}: not inside a git repository; skipping."
  exit 0
fi

cd "${repo_root}"

has_relevant_staged_changes=0
while IFS= read -r -d '' staged_path; do
  case "${staged_path}" in
    heru/*|tests/*)
      has_relevant_staged_changes=1
      break
      ;;
  esac
done < <(git diff --cached --name-only -z --diff-filter=ACMRD)

if [[ "${has_relevant_staged_changes}" -eq 0 ]]; then
  exit 0
fi

git_common_dir="$(git rev-parse --git-common-dir)"
git_common_dir="$(resolve_abs_path "${git_common_dir}")"
canonical_heru_root="$(cd "${git_common_dir}/.." && pwd -P)"
sibling_litehive="$(cd "${canonical_heru_root}/.." && pwd -P)/litehive"
litehive_repo="$(discover_litehive_repo "${sibling_litehive}" || true)"

if [[ -z "${litehive_repo}" ]]; then
  say "${HOOK_NAME}: staged changes touch heru/tests, but litehive was not found."
  say "${HOOK_NAME}: tried sibling path ${sibling_litehive} and env var LITEHIVE_REPO."
  say "${HOOK_NAME}: skipping litehive smoke tests."
  exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
  say "${HOOK_NAME}: staged changes touch heru/tests, but \`uv\` is not installed."
  say "${HOOK_NAME}: commit rejected because litehive smoke tests could not run."
  exit 1
fi

SAVED_STATE_DIR=""
if ! git diff --quiet --ignore-submodules -- || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  save_unstaged_state
fi

say "${HOOK_NAME}: staged changes touch heru/tests; running litehive smoke tests."
say "${HOOK_NAME}: litehive repo: ${litehive_repo}"

if ! (
  cd "${litehive_repo}" &&
    uv run pytest -q "${SMOKE_TESTS[@]}"
); then
  say "${HOOK_NAME}: litehive smoke tests failed."
  say "${HOOK_NAME}: commit rejected. Re-run the command above in ${litehive_repo} for details."
  exit 1
fi

say "${HOOK_NAME}: litehive smoke tests passed."
