# Deployment — Super magnet na klientov

## 1. Lokálne spustenie (najrýchlejšie)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Dokumentácia API: http://localhost:8000/docs
```

> **Pozor na `JWT_SECRET`.** Pri `APP_ENV=development` ho nie je potrebné
> nastavovať (vygeneruje sa dočasný secret, tokeny po reštarte neplatia). Pri
> produkčnom `APP_ENV` aplikácia odmietne naštartovať, kým ho nenastavíš.
> API počúva na `127.0.0.1`, nie na `0.0.0.0`.

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
# postgres: localhost:5432 (voliteľná, MVP používa SQLite)
```

Premenné prostredia sú v `infrastructure/dev.env`. GGUF modely sa montujú do
zviazku `model-cache` a `LLM_MODEL_PATH` ukazuje na `/models`. Porty sú
publikované len na `127.0.0.1`.

## 3. Model / GPU nastavenie (RX 7700 XT)

```bash
export LLM_MODEL_PATH=/abs/cesta/model.Q4_K_M.gguf
export LLM_GPU_LAYERS=-1     # všetky vrstvy na GPU
```

Pri 7B Q4_K_M (~4.5 GB) zostáva dostatok VRAM. Ak nestačí, zvoľ 3B model alebo
`LLM_GPU_LAYERS=0` (čistý CPU inference).

> Pred stiahnutím veľkého súboru si over, že repozitár na HuggingFace existuje.
> Pôvodné predvoľby `TheBloke/*` boli odstránené (HTTP 401) — použi mirror-y
> `bartowski/*` uvedené v `models/README.md`.

## 4. Tauri desktop

```bash
cd frontend
npm install
npm run tauri dev     # vývoj v desktop okne
npm run tauri build   # inštalátor (Windows/Linux)
```

> ⚠️ **Ešte to nefunguje.** `frontend/src-tauri/` v repozitári **neexistuje**,
> takže `npm run tauri build` zlyhá. `tauri.conf.json` je zatiaľ len kostra
> (opravený `distDir` na `dist`, zúžený HTTP allowlist, nastavený CSP).
> Vytvorenie Rust projektu patrí do Sprintu 4.

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

Na GitHubabe beží rovnaká kontrola v `.github/workflows/ci.yml` pri každom pushu
aj pull requeste.

## 7. Bezpečnosť

### Implementované

- Heslá: PBKDF2-SHA256, 100 000 iterácií, 16-bajtový salt (`services/auth.py`).
- JWT (HS256). `JWT_SECRET` je **povinný** pri `APP_ENV != development` —
  aplikácia odmietne naštartovať s prázdnym alebo placeholder hodnotou.
- CORS: wildcard `*` je odmietnutý, funguje len explicitný zoznam pôvod.
- Rate limit na prihlásenie (`LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_SECONDS`).
- `role` sa nedá poslať z klienta — admin je len prvý účet na čistej inštalácii.
- OAuth `state` sa generuje pri `/auth-url` a overuje sa pri `/callback`
  (ochrana proti CSRF); tokeny sa zapisujú s právami `0600`.
- Anti-CSV-injection pri exportoch (server aj XLSX vo fronte).
- LLM cache je ohraničená (LRU), generovanie je serializované lockom.
- LLM inference je výhradne lokálna; externé API len cez OAuth.

### Zatiaľ NIE je implementované

Tieto body sú v pôvodnej špecifikácii, ale v kóde **chýbajú**. Nezamieňaj ich
za hotové:

- **Šifrovanie v pokoji (AES-256)** — `ENCRYPTION_KEY_FILE` je len v konfigurácii,
  DB ani nahrávky sa nešifrujú.
- **Audit log** — žiadny záznam administrátorských akcií.
- **Mazanie osobných údajov (právo na výmaz)** — chýba endpoint.
- **GDPR pre e-mail** — chýba odhlásenie, bounce handling, suppression list,
  rate limit na odosielanie a súhlas. **Pred hromadným posielaním to musíš doplniť.**
- **Cookie s HttpOnly** — token je v `sessionStorage` (lepšie než `localStorage`,
  ale priebežne sa dá čítať skriptom na stránke).
