# Super magnet na klientov

**Lokálny, modulárny, open-source Apollo.io klon optimalizovaný pre slovenský B2B trh**
(ORSR, FinStat, Živnostenský register). Všetka LLM inference prebieha **lokálne**
cez [llama.cpp](https://github.com/ggerganov/llama.cpp) — žiadny cloud pre modely.

> 🎯 **Cieľový hardvér:** AMD Ryzen 5 5600 · 16 GB RAM · RX 7700 XT (12 GB VRAM).
> 📦 **Licencia:** MIT (pozri [`LICENSE`](./LICENSE)); použité open-source modely
> podliehajú vlastným licenciám (viď [`models/README.md`](./models/README.md)).

---

## ✨ Čo tento repozitár obsahuje (Sprint 0 / prvý artefakt)

Toto je **prvý bežný artefakt** podľa špecifikácie. Obsahuje:

- ✅ `README.md` s prehľadom a inštalačnými krokmi
- ✅ `infrastructure/docker-compose.yml` (backend, redis, db)
- ✅ **Minimálny FastAPI backend** s `POST /api/llm/prompt` → volá llama.cpp
  (mock fallback, ak model chýba)
- ✅ **Minimálny React + Tauri frontend** s jednou stránkou na odoslanie promptu
- ✅ `models/download_and_quantize.sh` (inštrukcie, nestahuje bez súhlasu)
- ✅ **Testy** pre backend endpoint (pytest, 7 testov)
- ✅ **OpenAPI spec** pre implementované endpointy (`docs/api_spec.yaml`)

Ďalšie moduly (auth, leady, enrichment, email, export, workflow, transkripcia)
sú rozvrhnuté v roadmape nižšie a v [`docs/architecture.md`](./docs/architecture.md).

---

## 🧱 Technolický stack

| Vrstva | Technológia |
|--------|-------------|
| Frontend | React + TypeScript + Tailwind CSS + Tauri (desktop) |
| Backend | FastAPI (Python) + Uvicorn; Celery + Redis (background) |
| LLM runtime | llama.cpp / GGUF (kvantizované 4/8-bit) |
| Embeddings / Vector DB | sentence-transformers + FAISS |
| ASR | whisper.cpp (transkripcia) |
| DB | SQLite (MVP) / PostgreSQL (produkcia) |
| Export | SheetJS (XLSX), Google Sheets/Docs API |
| Integrácie | HubSpot, Gmail, Microsoft Graph (OAuth) |
| CI | GitHub Actions (lint, testy, build) |

---

## 🚀 Rýchly štart

### A) Docker Compose (odporúčané)
```bash
docker compose -f infrastructure/docker-compose.yml up --build
# Backend API:        http://localhost:8000  (docs: /docs)
# Redis:              localhost:6379
# PostgreSQL (vol.):  localhost:5432
```

### B) Lokálne (bez Docker)
```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Frontend
cd frontend
npm install && npm run dev   # http://localhost:1420
```

### C) Jednoklikový inštalátor (Linux/WSL/macOS)
```bash
bash install.sh
```

> 💡 Bez GGUF modelu backend beží v **mock** režime — endpoint je plne volateľný
> a testy prechádzajú. Pre reálnu inference stiahni model (krok nižšie).

---

## 🤖 Nastavenie lokálneho modelu

```bash
cd models
bash download_and_quantize.sh --list                 # dostupné predvoľby
bash download_and_quantize.sh download --preset 7b   # Mistral-7B Q4_K_M
export LLM_MODEL_PATH="$PWD/gguf/mistral-7b-instruct-v0.3.Q4_K_M.gguf"
export LLM_GPU_LAYERS=-1                             # RX 7700 XT
```
Podrobnosti: [`models/README.md`](./models/README.md).

---

## 🔌 Príklady volania API (curl)

**Zdravotný stav**
```bash
curl http://localhost:8000/health
```

**Spustenie promptu (mock režim)**
```bash
curl -X POST http://localhost:8000/api/llm/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Ohodnoť lead: IT firma, 50 zamestnancov, rast tržieb.",
    "model_hint": "7b",
    "top_k": 40,
    "max_tokens": 256,
    "temperature": 0.7,
    "use_rag": false
  }'
```

**Stav LLM Orchestratora**
```bash
curl http://localhost:8000/api/llm/status
```

### Sprint 1 — Auth, Leads, Embeddings

**Registrácia + login (JWT)**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123","role":"admin"}'

TOK=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**Vytvorenie leadu (ORSR enrichment, ak je IČO)**
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"company_name":"Acme s.r.o.","ico":"12345678","email":"a@acme.sk","sector":"IT"}'
```

**LLM lead scoring (0–100)**
```bash
curl -X POST http://localhost:8000/api/leads/1/score -H "Authorization: Bearer $TOK"
```

**CSV import**
```bash
curl -X POST http://localhost:8000/api/leads/import \
  -H "Authorization: Bearer $TOK" \
  -F "file=@leads.csv;type=text/csv"
```

**Embeddings: upsert + search**
```bash
curl -X POST http://localhost:8000/api/embeddings/upsert \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"doc_id":"n1","text":"Lead scoring pre IT firmu na Slovensku"}'

curl "http://localhost:8000/api/embeddings/search?q=IT%20firma&top_k=3" \
  -H "Authorization: Bearer $TOK"
```

> 🔒 Endpointy `/api/leads` a `/api/embeddings` vyžadujú JWT (`Authorization: Bearer <token>`).


---

## 🧪 Testovanie

```bash
cd backend && pytest          # 7 testov (mock backend, žiadne sťahovanie)
cd frontend && npm run build  # TypeScript + Vite build
```

---

## 🗺️ Roadmapa (sprinty)

| Sprint | Výstup | Stav |
|--------|--------|------|
| **0 — Setup** | Repo scaffold, Docker Compose, FastAPI, React, README | ✅ commit `eca9d3d` |
| **1 — MVP core** | Auth (JWT), lead CRUD, CSV import, ORSR connector, LLM Orchestrator (7B), FAISS embeddings | ✅ implementované (tento commit) |
| **2** | Gmail integrácia, sekvencie, dashboard, export XLSX/Sheets | 📋 plánované |
| **3** | Workflow builder, A/B testy, deliverability, transkripcia | 📋 plánované |
| **4** | HubSpot sync, reports, Tauri packaging, inštalátory | 📋 plánované |

Každý modul bude mať: kód, unit + integračné testy, dokumentáciu, curl príklady
a E2E demo scenár (import CSV → enrichment → scoring → email → export XLSX).

---

## 🔐 Bezpečnosť a súkromie (§10)

- DB súbory a nahrávky šifrované **AES-256**; kľúč lokálne v chránenom súbore.
- LLM inference **výhradne lokálne**; žiadne cloud závislosti pre modely.
- Externé API (HubSpot, Google, Gmail) len cez **OAuth**.
- Možnosť vymazať všetky osobné údaje; audit logy admin akcií.

---

## 📂 Štruktúra repozitára

```
backend/        FastAPI app, služby, testy
frontend/       React + Tailwind + Tauri
infrastructure/ docker-compose, dev.env
models/         download & quantize skripty
docs/           architecture, OpenAPI spec, deployment
install.sh      jednoklikový inštalátor
```

---

## 📜 Licencia

Kód: **MIT** (pozri [`LICENSE`](./LICENSE)). Open-source modely (Mistral, Qwen,
atď.) podliehajú ich vlastným licenciám — over ich pred komerčným použitím.
