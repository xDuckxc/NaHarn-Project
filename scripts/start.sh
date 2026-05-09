#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PROJECT_ROOT
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "$PROJECT_ROOT"

if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
  echo "DEEPSEEK_API_KEY is required. Put it in .env, then run docker compose up --build."
  exit 1
fi

if [ "${APP_AUTO_LOAD_DB:-true}" = "true" ]; then
  python -m naharn.db_loader --init-db --csv "${PRODUCT_CSV:-data/mall_products_500_with_3d.csv}" --skip-if-loaded
fi

exec chainlit run src/naharn/app.py --host "${CHAINLIT_HOST:-0.0.0.0}" --port "${CHAINLIT_PORT:-8000}"
