#!/usr/bin/env bash
set -euo pipefail

# Staging-first release branch promotion helper (Option B).
# This script does NOT run git commands automatically for promotion; it prints the exact commands.
# It may run staging gates if BASE is provided.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required." >&2
  exit 1
fi

# Require clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree is not clean. Commit or stash changes before promotion." >&2
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: Must run from main branch (staging). Current: $CURRENT_BRANCH" >&2
  exit 1
fi

echo "Fetching origin..."
git fetch origin

LEFT_RIGHT_COUNTS="$(git rev-list --left-right --count origin/main...HEAD)"
BEHIND_COUNT="$(echo "$LEFT_RIGHT_COUNTS" | awk '{print $1}')"
AHEAD_COUNT="$(echo "$LEFT_RIGHT_COUNTS" | awk '{print $2}')"

if [[ "$BEHIND_COUNT" != "0" ]]; then
  echo "ERROR: main is behind origin/main by $BEHIND_COUNT commits. Pull/rebase first." >&2
  exit 1
fi
if [[ "$AHEAD_COUNT" != "0" ]]; then
  echo "ERROR: main is ahead of origin/main by $AHEAD_COUNT commits. Push or reconcile before promotion." >&2
  exit 1
fi

MAIN_SHA="$(git rev-parse HEAD)"
echo "Staging-tested commit (main HEAD): $MAIN_SHA"

if [[ -z "${BASE:-}" ]]; then
  echo "INFO: BASE not provided. Run staging gate before promotion:" >&2
  echo "  MODE=staging BASE=https://<staging>.railway.app ./scripts/promotion_gate.sh" >&2
  echo "Then rerun this script with BASE set to capture gate evidence." >&2
else
  echo "Running staging promotion gate (MODE=staging)..."
  MODE=staging BASE="$BASE" bash "$SCRIPT_DIR/promotion_gate.sh"
  echo "Staging gate completed."
fi

echo
echo "Promotion commands (review, then run manually):"
cat <<EOF
git fetch origin
git checkout release
git merge --ff-only origin/main
git push origin release
# After promotion, run prod smoke:
MODE=prod BASE=https://<prod>.railway.app ./scripts/promotion_gate.sh
# Then append docs/RELEASE_LOG.md with promotion entry for $MAIN_SHA
EOF

echo
echo "Rollback commands (manual, use only if needed and adjust SHA):"
cat <<EOF
git fetch origin
git checkout release
git reset --hard <previous_good_sha>
git push --force-with-lease origin release
MODE=prod BASE=https://<prod>.railway.app ./scripts/promotion_gate.sh
# Append rollback entry in docs/RELEASE_LOG.md
EOF

echo
echo "Reminder:"
echo "- APP_ENV must be staging on staging, production on prod; DEBUG_ERRORS=0."
echo "- No direct prod deploys; prod advances only via release branch fast-forward."
echo "- Log every promotion/rollback in docs/RELEASE_LOG.md (append-only)."
