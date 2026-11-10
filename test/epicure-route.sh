#!/usr/bin/env bash
# Run the Epicure route question used by the classification tests.
#
#   ./epicure-route.sh
#   ./epicure-route.sh 'New Product called LANTANA with values like VIOLAS.'
set -euo pipefail
cd "$(dirname "$0")/classifier"

PY="/home/jerry/keprompt/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
    PY=python3
fi

QUESTION="${*:-New Product called LANTANA with values like VIOLAS.}"

exec "$PY" -m keprompt chats create prompt/classifier.prompt --json --set "question=${QUESTION}"
