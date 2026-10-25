#!/usr/bin/env bash
# Publish the existing offline evidence, then commit/push only its research bundle.
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TASK_WORKTREE="$(dirname -- "$TASK_ROOT")/SIGN-SRU-reward-review"
TASK_BRANCH="docs/qwen-reward-review-20261013"
TASK_BUNDLE="docs/research/qwen_relative_diagnostic_2026-10-13"
TASK_PYTHON="${SIGN_PUBLISH_PYTHON:-/scratch/e1538633/liuyi/envs/sign/bin/python}"
TASK_CHECK_ONLY=0
case "${1:-}" in
  '') [[ $# == 0 ]] || { echo 'Usage: sync_research_github.sh [--check-only]' >&2; exit 1; } ;;
  --check-only) [[ $# == 1 ]] || exit 1; TASK_CHECK_ONLY=1 ;;
  *) echo 'Usage: sync_research_github.sh [--check-only]' >&2; exit 1 ;;
esac
stop() { echo "STOP: $* No automatic history repair or deletion will be attempted." >&2; exit 1; }
git_task() { git -C "$TASK_WORKTREE" "$@"; }
[[ "$(git_task rev-parse --show-toplevel)" == "$TASK_WORKTREE" ]] || stop 'Unexpected worktree.'
[[ "$(git_task symbolic-ref --quiet --short HEAD)" == "$TASK_BRANCH" ]] || stop 'Wrong publication branch.'
case "$(git_task remote get-url origin)" in
  git@github.com:yiichu03/SIGN-SRU.git|https://github.com/yiichu03/SIGN-SRU.git) ;;
  *) stop 'origin must be yiichu03/SIGN-SRU.' ;;
esac
TASK_GIT_DIR="$(git_task rev-parse --absolute-git-dir)"
exec 9> "$TASK_GIT_DIR/research-sync.lock"
flock -n 9 || stop 'Another synchronization is running.'
for TASK_MARKER in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
  [[ ! -e "$(git_task rev-parse --git-path "$TASK_MARKER")" ]] || stop 'An unfinished Git operation exists.'
done
[[ -z "$(git_task status --porcelain --untracked-files=all)" ]] || stop 'Publication worktree has existing edits; preserve and inspect them first.'
git_task fetch --no-tags origin "refs/heads/$TASK_BRANCH"
TASK_REMOTE_HEAD="$(git_task rev-parse FETCH_HEAD)"
git_task merge-base --is-ancestor "$TASK_REMOTE_HEAD" HEAD || stop 'Remote is ahead or histories diverged. Inspect without forcing a merge.'
while IFS= read -r TASK_COMMIT; do
  while IFS= read -r TASK_PATH; do
    [[ -z "$TASK_PATH" || "$TASK_PATH" == "$TASK_BUNDLE/"* ]] || stop "An unpushed commit changes a file outside the bundle: $TASK_PATH"
  done < <(git_task diff-tree --no-commit-id --name-only -r "$TASK_COMMIT")
done < <(git_task rev-list "$TASK_REMOTE_HEAD..HEAD")
if [[ "$TASK_CHECK_ONLY" == 1 ]]; then
  "$TASK_PYTHON" "$TASK_ROOT/scripts/publish_relative_diagnostic.py" --check-only
  echo 'Check complete; no publication files, commits or remote branches changed.'
  exit 0
fi
"$TASK_PYTHON" "$TASK_ROOT/scripts/publish_relative_diagnostic.py"
git_task status --short
git_task diff --stat
git_task -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check
while IFS= read -r TASK_PATH; do
  [[ -z "$TASK_PATH" || "$TASK_PATH" == "$TASK_BUNDLE/"* ]] || stop "Unexpected changed file: $TASK_PATH"
done < <(git_task diff --name-only)
while IFS= read -r TASK_PATH; do
  [[ -z "$TASK_PATH" || "$TASK_PATH" == "$TASK_BUNDLE/"* ]] || stop "Unexpected new file: $TASK_PATH"
done < <(git_task ls-files --others --exclude-standard)
[[ "$(git_task symbolic-ref --quiet --short HEAD)" == "$TASK_BRANCH" ]] || stop 'Branch changed during publication.'
git_task -c core.autocrlf=false add -- "$TASK_BUNDLE"
git_task -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check
if ! git_task diff --cached --quiet; then
  git_task commit -m 'docs: synchronize SIGN research materials'
else
  echo 'No material changes; no new commit created.'
fi
git_task push origin "HEAD:refs/heads/$TASK_BRANCH"
TASK_HEAD="$(git_task rev-parse HEAD)"
TASK_PUSHED="$(git_task ls-remote --heads origin "refs/heads/$TASK_BRANCH" | cut -f1)"
[[ "$TASK_PUSHED" == "$TASK_HEAD" ]] || stop 'Remote moved after push; inspect the published history.'
echo "Published commit: $TASK_HEAD"
echo "https://github.com/yiichu03/SIGN-SRU/blob/$TASK_HEAD/$TASK_BUNDLE/README.md"
