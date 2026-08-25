# Deployment — Super magnet na klientov

## 1. Lokálne spustenie (najrýchlejšie)

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Dokumentácia API: http://localhost:8000/docs
```

### Frontend (Vite dev)
```bash
cd frontend
npm install
npm run dev                # http://localhost:1420
```

> Bez GGUF modelu backend beží v **mock** režime — API je plne volateľné.
> Pre reálnu inference pozri `models/README.md`.

## 2. Docker Compose (dev)

```bash
docker compose -f infrastructure/docker-compose.yml up --build
# backend:  http://localhost:8000
# redis:    localhost:6379
# postgres: localhost:5432 (voliteľné, MVP používa SQLite)
```

Premenné prostredia sú v `infrastructure/dev.env`. GGUF modely sa montujú do
zväzku `model-cache` a `LLM_MODEL_PATH` ukazuje na `/models`.

## 3. Model / GPU nastavenie (RX 7700 XT)

```bash
export LLM_MODEL_PATH=/abs/cesta/model.Q4_K_M.gguf
export LLM_GPU_LAYERS=-1     # všetky vrstvy na GPU
```

Pri 7B Q4_K_M (~4.5 GB) zostáva dostatok VRAM. Ak nestačí, zvoľ 3B model alebo
`LLM_GPU_LAYERS=0` (CPU).

## 4. Tauri desktop (Sprint 4)

```bash
cd frontend
npm install
npm run tauri dev     # vývoj v桌面 okne
npm run tauri build   # inštalátor (Windows/Linux)
```
Poznámka: `tauri.conf.json` je pripravený; `src-tauri/` rustový projekt sa pridá
v Sprinte 4 (packaging).

## 5. Jednoklikový inštalátor

```bash
bash install.sh       # Linux/macOS (WSL na Windows)
```
Skript vytvorí Python venv, nainštaluje backend závislosti, spustí `npm install`
vo frontere, pripraví `.env` config a spustí backend. Sťahovanie modelov je
voliteľné (interaktívne).

## 6. Testovanie

```bash
# Backend
cd backend && pytest

# Frontend (build + lint)
cd frontend && npm run build && npm run lint
```

## 7. Bezpečnosť (§10)

- DB súbory a nahrávky šifrované AES-256; kľúč v chránenom súbore.
- Citlivé dáta len lokálne; žiadny cloud pre LLM.
- Externé API (HubSpot, Google, Gmail) výhradne cez OAuth.
- Možnosť vymazať všetky osobné údaje používateľa.
