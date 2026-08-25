#!/usr/bin/env bash
# =============================================================================
# install.sh — jednoklikový inštalátor (Linux / macOS / WSL).
# Inštaluje backend (venv), frontend (npm), pripraví .env a spustí backend.
# Sťahovanie LLM modelov je voliteľné (interaktívne).
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> Super magnet na klientov — inštalácia"

# ---- Backend ---------------------------------------------------------------
echo "==> Backend: venv + závislosti"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# ---- Frontend --------------------------------------------------------------
echo "==> Frontend: npm install"
cd "$ROOT/frontend"
if command -v npm >/dev/null 2>&1; then
  npm install -q
else
  echo "UPOZORNENIE: npm nie je dostupné — frontend nebol nainštalovaný." >&2
fi

# ---- Konfigurácia ----------------------------------------------------------
echo "==> Konfigurácia (.env)"
if [[ ! -f "$ROOT/infrastructure/dev.env" ]]; then
  cat > "$ROOT/infrastructure/dev.env" <<'EOF'
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./app.db
REDIS_URL=redis://localhost:6379/0
LLM_MODEL_PATH=
LLM_GPU_LAYERS=-1
JWT_SECRET=change-me-in-production
VITE_API_BASE=http://localhost:8000
EOF
fi

# ---- Voliteľné stiahnutie modelu ------------------------------------------
read -r -p "Stiahnuť lokálny LLM model teraz? (y/N): " DL
if [[ "${DL,,}" == "y" ]]; then
  bash "$ROOT/models/download_and_quantize.sh" download --preset 7b || \
    echo "Sťahovanie zlyhalo — model môžeš pridať neskôr (models/README.md)."
fi

# ---- Spustenie -------------------------------------------------------------
read -r -p "Spustiť backend teraz? (y/N): " RUN
if [[ "${RUN,,}" == "y" ]]; then
  cd "$ROOT/backend"
  source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

echo "==> Inštalácia dokončená. Frontend: cd frontend && npm run dev"
