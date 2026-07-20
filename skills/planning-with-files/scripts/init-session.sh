#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Initialize legacy-root or isolated JSON-canonical planning sessions.
# SCOPE: Resolve session directory, delegate state creation, and set active plan pointer.
# DEPENDS: Bash, Python 3, and scripts/planning-state.py.
# END_MODULE_CONTRACT
set -eu

TEMPLATE="default"
PROJECT_NAME=""
USE_PLAN_DIR=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --template|-t) TEMPLATE="$2"; shift 2 ;;
        --plan-dir) USE_PLAN_DIR=1; shift ;;
        *) PROJECT_NAME="${PROJECT_NAME:+$PROJECT_NAME }$1"; shift ;;
    esac
done
case "$TEMPLATE" in default|analytics) ;; *) echo "Unknown template: $TEMPLATE" >&2; exit 2 ;; esac

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DATE_VALUE="$(date +%Y-%m-%d)"

slugify() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9]/-/g' -e 's/-\{2,\}/-/g' -e 's/^-//' -e 's/-$//' | cut -c1-40
}

if [ -n "$PROJECT_NAME" ] || [ "$USE_PLAN_DIR" -eq 1 ]; then
    SLUG="$(slugify "$PROJECT_NAME")"
    [ -n "$SLUG" ] || SLUG="untitled-$(date +%H%M%S)"
    PLAN_ID="$DATE_VALUE-$SLUG"
    PLAN_ROOT="$PWD/.planning"
    COUNTER=2
    while [ -d "$PLAN_ROOT/$PLAN_ID" ]; do PLAN_ID="$DATE_VALUE-$SLUG-$COUNTER"; COUNTER=$((COUNTER + 1)); done
    PLAN_DIR="$PLAN_ROOT/$PLAN_ID"
    mkdir -p "$PLAN_DIR"
    python3 "$SCRIPT_DIR/planning-state.py" init "$PLAN_DIR" --template "$TEMPLATE" --created "$DATE_VALUE"
    printf '%s\n' "$PLAN_ID" > "$PLAN_ROOT/.active_plan"
    echo "PLAN_ID=$PLAN_ID"
    echo "Active plan recorded: $PLAN_ROOT/.active_plan"
else
    python3 "$SCRIPT_DIR/planning-state.py" init "$PWD" --template "$TEMPLATE" --created "$DATE_VALUE"
fi
