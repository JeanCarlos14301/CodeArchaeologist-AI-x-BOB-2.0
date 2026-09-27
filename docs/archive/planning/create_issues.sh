#!/usr/bin/env bash
# Creates one GitHub issue for each row in the historical task table.
# Labels: person (jean, felipe, daniel, edgar) and milestone (milestone:H3 ... milestone:H44).
# Idempotent: skips IDs that already have an issue whose title begins with "[ID]".
#
# Requirements: authenticated gh CLI; run from the repository root or set GH_REPO=owner/repo.
# Usage:        docs/archive/planning/create_issues.sh
#               DRY_RUN=1 docs/archive/planning/create_issues.sh
set -euo pipefail

TASKS_FILE="${TASKS_FILE:-docs/archive/planning/tasks.md}"
DRY_RUN="${DRY_RUN:-0}"

command -v gh >/dev/null || { echo "gh CLI is not installed" >&2; exit 1; }
[[ -f "$TASKS_FILE" ]] || { echo "$TASKS_FILE does not exist" >&2; exit 1; }

run() {
  if [[ "$DRY_RUN" == "1" ]]; then printf '[dry-run]'; printf ' %q' "$@"; echo; else "$@"; fi
}

trim() { sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' <<<"$1"; }

milestone_for() {
  # Assigns the milestone from the end of the window (for example H8–H14 -> 14 -> milestone:H24).
  local window="$1" end
  end="$(grep -oE 'H[0-9]+' <<<"$window" | tail -n1 | tr -d 'H')"
  if [[ -z "$end" ]]; then echo "milestone:continuous"
  elif (( end <= 3 )); then echo "milestone:H3"
  elif (( end <= 8 )); then echo "milestone:H8"
  elif (( end <= 24 )); then echo "milestone:H24"
  elif (( end <= 32 )); then echo "milestone:H32"
  else echo "milestone:H44"
  fi
}

echo "Creating labels..."
for label in jean felipe daniel edgar; do
  run gh label create "$label" --color 1f6feb --description "Task owned by $label" --force
done
for label in milestone:H3 milestone:H8 milestone:H24 milestone:H32 milestone:H44 milestone:continuous; do
  run gh label create "$label" --color fbca04 --description "$label" --force
done

echo "Creating issues from $TASKS_FILE..."
grep -E '^\|[[:space:]]*[JFDE]-[0-9]{2}[[:space:]]*\|' "$TASKS_FILE" |
while IFS='|' read -r _ id owner window task acceptance _; do
  id="$(trim "$id")"; owner="$(trim "$owner")"; window="$(trim "$window")"
  task="$(trim "$task")"; acceptance="$(trim "$acceptance")"
  person="$(tr '[:upper:]' '[:lower:]' <<<"$owner")"
  milestone="$(milestone_for "$window")"
  title="[$id] $task"

  if [[ "$DRY_RUN" != "1" ]] && \
     [[ "$(gh issue list --state all --search "\"[$id]\" in:title" --json title --jq "map(select(.title | startswith(\"[$id]\"))) | length")" != "0" ]]; then
    echo "Skipped $id (already exists)"
    continue
  fi

  body="$(printf '**ID:** %s\n\n**Owner:** %s\n\n**Window:** %s\n\n## Description\n%s\n\n## Acceptance criterion\n- [ ] %s\n\nSource: `%s`\n' \
    "$id" "$owner" "$window" "$task" "$acceptance" "$TASKS_FILE")"
  run gh issue create --title "$title" --body "$body" --label "$person,$milestone"
done
echo "Done."
