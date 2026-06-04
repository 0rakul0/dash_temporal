#!/usr/bin/env bash
set -euo pipefail

echo "Starting Dash app"
echo "PORT=${PORT:-not-set}"
echo "PWD=$(pwd)"
echo "Python=$(python --version)"

test -f app.py
test -f requirements.txt
test -f saida/analises/RJ/retornos_apos_exoneracao.csv
test -f saida/analises/RJ/movimentacoes_pessoas.parquet

exec gunicorn app:server \
  --bind "0.0.0.0:${PORT}" \
  --workers 1 \
  --threads 2 \
  --timeout 180 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
