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

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m compileall -q app.py exposibot tests migrations
python -m unittest discover -s tests -v

python -m flask --app app db upgrade

python - <<'PY'
from app import app
with app.test_client() as client:
    health = client.get('/healthz')
    ready = client.get('/readyz')
    assert health.status_code == 200, health.status_code
    assert ready.status_code == 200, ready.status_code
print('Health/readiness checks: OK')
PY

printf '\nDeploy de código concluído. No painel Web do PythonAnywhere, clique em Reload para reiniciar a aplicação.\n'
