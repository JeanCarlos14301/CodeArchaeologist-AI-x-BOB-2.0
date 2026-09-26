#!/usr/bin/env bash
# Crea un issue de GitHub por cada fila de la tabla de docs/tasks.md.
# Etiquetas: persona (jean, felipe, daniel, edgar) e hito (hito:H3 ... hito:H44, hito:continuo).
# Es idempotente: omite IDs que ya tienen un issue con "[ID]" en el título.
#
# Requisitos: gh CLI autenticado y ejecutar desde la raíz del repo (o con GH_REPO=owner/repo).
# Uso:        scripts/create_issues.sh           # crea los issues
#             DRY_RUN=1 scripts/create_issues.sh # solo muestra lo que haría
set -euo pipefail

TASKS_FILE="${TASKS_FILE:-docs/tasks.md}"
DRY_RUN="${DRY_RUN:-0}"

command -v gh >/dev/null || { echo "gh CLI no está instalado" >&2; exit 1; }
[[ -f "$TASKS_FILE" ]] || { echo "No existe $TASKS_FILE" >&2; exit 1; }

run() {
  if [[ "$DRY_RUN" == "1" ]]; then printf '[dry-run]'; printf ' %q' "$@"; echo; else "$@"; fi
}

trim() { sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' <<<"$1"; }

milestone_for() {
  # Asigna el hito según la hora final de la ventana (ej. "H8–H14" -> 14 -> hito:H24).
  local window="$1" end
  end="$(grep -oE 'H[0-9]+' <<<"$window" | tail -n1 | tr -d 'H')"
  if [[ -z "$end" ]]; then echo "hito:continuo"
  elif (( end <= 3 )); then echo "hito:H3"
  elif (( end <= 8 )); then echo "hito:H8"
  elif (( end <= 24 )); then echo "hito:H24"
  elif (( end <= 32 )); then echo "hito:H32"
  else echo "hito:H44"
  fi
}

echo "Creando etiquetas..."
for label in jean felipe daniel edgar; do
  run gh label create "$label" --color 1f6feb --description "Tarea de $label" --force
done
for label in hito:H3 hito:H8 hito:H24 hito:H32 hito:H44 hito:continuo; do
  run gh label create "$label" --color fbca04 --description "Hito $label" --force
done

echo "Creando issues desde $TASKS_FILE..."
grep -E '^\|[[:space:]]*[JFDE]-[0-9]{2}[[:space:]]*\|' "$TASKS_FILE" |
while IFS='|' read -r _ id owner window task acceptance _; do
  id="$(trim "$id")"; owner="$(trim "$owner")"; window="$(trim "$window")"
  task="$(trim "$task")"; acceptance="$(trim "$acceptance")"
  person="$(tr '[:upper:]' '[:lower:]' <<<"$owner")"
  milestone="$(milestone_for "$window")"
  title="[$id] $task"

  if [[ "$DRY_RUN" != "1" ]] && \
     [[ "$(gh issue list --state all --search "\"[$id]\" in:title" --json title --jq "map(select(.title | startswith(\"[$id]\"))) | length")" != "0" ]]; then
    echo "Omitido $id (ya existe)"
    continue
  fi

  body="$(printf '**ID:** %s\n\n**Dueño:** %s\n\n**Ventana:** %s\n\n## Descripción\n%s\n\n## Criterio de aceptación\n- [ ] %s\n\nFuente: `%s`\n' \
    "$id" "$owner" "$window" "$task" "$acceptance" "$TASKS_FILE")"
  run gh issue create --title "$title" --body "$body" --label "$person,$milestone"
done
echo "Listo."
