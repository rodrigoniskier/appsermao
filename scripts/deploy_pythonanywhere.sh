#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

printf '\n== Exposibot / PythonAnywhere deployment ==\n'

mkdir -p backups
DB_PATH="instance/exposibot.db"
if [[ -f "$DB_PATH" ]]; then
    STAMP="$(date +%Y%m%d_%H%M%S)"
    cp "$DB_PATH" "backups/exposibot_${STAMP}.db"
    echo "Backup SQLite criado: backups/exposibot_${STAMP}.db"
fi

# Use an active virtualenv when one exists. Otherwise reuse a project-local
# environment or create .venv. This prevents dependency changes from leaking
# into the account-wide Python user site (for example Dash/Flask conflicts).
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
    VENV_PATH="${VIRTUAL_ENV}"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
    VENV_PATH="$ROOT/.venv"
elif [[ -x "$ROOT/venv/bin/python" ]]; then
    PYTHON="$ROOT/venv/bin/python"
    VENV_PATH="$ROOT/venv"
else
    BASE_PYTHON="${PYTHON_BIN:-}"
    if [[ -z "$BASE_PYTHON" ]]; then
        if command -v python3.13 >/dev/null 2>&1; then
            BASE_PYTHON="$(command -v python3.13)"
        elif command -v python3 >/dev/null 2>&1; then
            BASE_PYTHON="$(command -v python3)"
        else
            BASE_PYTHON="$(command -v python)"
        fi
    fi
    echo "Nenhum virtualenv do projeto encontrado; criando $ROOT/.venv com $BASE_PYTHON"
    "$BASE_PYTHON" -m venv "$ROOT/.venv"
    PYTHON="$ROOT/.venv/bin/python"
    VENV_PATH="$ROOT/.venv"
fi

echo "Python de deploy: $PYTHON"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

"$PYTHON" -m compileall -q app.py exposibot tests migrations
"$PYTHON" -m unittest discover -s tests -v

"$PYTHON" -m flask --app app db upgrade

"$PYTHON" - <<'PY'
from app import app
with app.test_client() as client:
    health = client.get('/healthz')
    ready = client.get('/readyz')
    assert health.status_code == 200, health.status_code
    assert ready.status_code == 200, ready.status_code
print('Health/readiness checks: OK')
PY

printf '\nDeploy de código concluído.\n'
printf 'Virtualenv usado: %s\n' "$VENV_PATH"
printf 'No painel Web do PythonAnywhere, confirme que o campo Virtualenv aponta para esse diretório e então clique em Reload.\n'
