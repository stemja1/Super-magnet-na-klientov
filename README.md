# Super magnet na klientov

**Lokálny, modulárny, open-source Apollo.io klon optimalizovaný pre slovenský B2B trh**
(ORSR, Živnostenský register). Všetka LLM inference prebieha **lokálne**
cez [llama.cpp](https://github.com/ggerganov/llama.cpp) — žiadny cloud pre modely.

> ⚠️ **Budú k úprimní:** repozitár má funkčný backbone (auth, leady, sekvencie,
> workflow, export, embeddings) a 95 testov, ale **chýba mu zdroj dát** —
> aplikácii nevie nájsť firmy, vie len importovať CSV. Toto je najväčší
> rozdiel oproti Apollo.io. Zoznam ďalších medzier je nižšie.

> 🎯 **Cieľový hardvér:** AMD Ryzen 5 5600 · 16 GB RAM · RX 7700 XT (12 GB VRAM).
> 📦 **Licencia:** MIT (pozri [`LICENSE`](./LICENSE)); použité open-source modely
> podliehajú vlastným licenciám (viď [`models/README.md`](./models/README.md)).


---

## ✨ Čo tento repozitár obsahuje

Stav k **2026-10-03** — Sprinty 0–3 implementované. Kód, unit testy, dokumentácia
a CI sú hotové; viacero modulov však **beží v mock/sandbox režime** a niektoré
body pôvodnej špecifikácie (pozri nižšie) **chýbajú**.

### Reálne funguje

- **Auth** — PBKDF2-SHA256 heslá + JWT (HS256), rate limit na prihlásenie,
  CORS cez explicitný zoznam, `JWT_SECRET` povinný mimo development
- **Leads** — CRUD, CSV import (aj s BOM), filter, LLM lead scoring 0–100
- **Sequences** — enroll/run, A/B varianty, idempotentný enroll, izolácia
  zlyhaní v dávke
- **Workflow builder** — `score`, `send_email`, `enrich`, `log`, `wait`
  (reálne pozastavenie s pokračovaním), `condition` s vnorenými vetvami
- **Embeddings + RAG** — sentence-transformers/FAISS s numpy fallbackom,
  `use_rag` naozaj číta z vektorového store, endpoint `/api/embeddings/info`
  hlási, či sú vektory sémantické
- **Deliverability** — SPF/DKIM/DMARC report
- **Export** — CSV (s ochranou proti CSV injection), XLSX (SheetJS),
  Google Sheets/Docs
- **Transkripcia** — whisper.cpp + LLM call insights
- **CI** — `.github/workflows/ci.yml`: pytest + typecheck/build/lint

### Len mock / sandbox (neposiela, nestahuje, nevyhľadáva)

- **LLM** — bez GGUF modelu vracia `[MOCK]` text. Žiadna reálna inferencia.
- **ORSR** — scrapuje HTML z `or.sr` heuristickým regexom (nemá verejné API).
- **Gmail** — bez `GMAIL_CLIENT_ID/SECRET` je `mode: sandbox`.
- **Whisper** — bez `WHISPER_MODEL` vracia simulovaný prepis.
- **Google Sheets/Docs** — sandbox odpoveď.

### Chýba (a je to dôležité)

- **Zdroj dát.** Apollo.io je predovšetkým *databáza* firiem a kontaktov na
  vyhľadávanie. Táto aplikácia vie len importovať CSV, ktoré si musíš sám
  zbierať. Bez zdroja dát to nie je Apollo klon.
- **Automatické spúšťanie sekvencií** — chýba Celery worker a plánovač;
  `POST /api/sequences/{id}/run` sa volá ručne.
- **GDPR pre e-mail** — odhlásenie, bounce handling, suppression list, súhlas.
  Bez toho hrozí, že emaily skončia v spame.
- **Šifrovanie v pokoji (AES-256)** a **audit log** — sľúbené v pôvodnom
  README, v kóde nie sú.
- **Tauri desktop build** — `frontend/src-tauri/` neexistuje, `tauri build`
  zlyhá.
- **HubSpot/CRM sync, reporty** — nahlásované, neimplementované.

Podrobný rozpad je v [`docs/architecture.md`](./docs/architecture.md).


---

## 🧱 Technolický stack

| Vrstva | Technológia |
|--------|-------------|
| Frontend | React 18 + TypeScript + Tailwind CSS (Tauri desktop — rozpracované) |
| Backend | FastAPI (Python 3.11) + Uvicorn |
| LLM runtime | llama.cpp / GGUF (kvantizované 4/8-bit), mock fallback |
| Embeddings / Vector store | sentence-transformers + FAISS (numpy fallback) |
| ASR | whisper.cpp (`whisper-cli`) |
| DB | SQLite (MVP) / PostgreSQL (produkcia) |
| Export | SheetJS 0.20.3 (XLSX), Google Sheets/Docs API |
| Integrácie | Gmail, Google Sheets/Docs (OAuth) |
| CI | GitHub Actions (pytest + typecheck/build/lint) |
| Plánované | Celery + Redis (scheduler), HubSpot/CRM sync |


---

## 🚀 Rýchly štart

### A) Docker Compose (odporúčané)
```bash
docker compose -f infrastructure/docker-compose.yml up --build
# Backend API:        http://localhost:8000  (docs: /docs)
# Redis:              localhost:6379
# PostgreSQL (vol.):  localhost:5432
```
> Porty sú publikované len na `127.0.0.1`. Docker Compose nespúšťa frontend —
> ten beží cez `npm run dev` (bod B) alebo Tauri.

### B) Lokálne (bez Docker)
```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

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
bash download_and_quantize.sh download --preset 7b   # Mistral-7B Q4_K_M (mirror bartowski)
export LLM_MODEL_PATH="$PWD/gguf/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
export LLM_GPU_LAYERS=-1                             # RX 7700 XT
```

> ⚠️ Pôvodné predvoľby `TheBloke/*` boli z HuggingFace **odstránené** (HTTP 401).
> Skript teraz používa mirror-y `bartowski/*` a pred stiahnutím veľkého súboru
> overí dostupnosť repozitára. Podrobnosti: [`models/README.md`](./models/README.md).


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
# `role` sa NEPOSIELA — prvý účet na čistej inštalácii sa stane adminom,
# každý ďalší je bežný používateľ.
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'

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

**Embeddings: stav, upsert, search**
```bash
# Skutočný stav: backend hlási či sú vektory sémantické alebo len hashované
curl http://localhost:8000/api/embeddings/info -H "Authorization: Bearer $TOK"
# {"backend":"hashing","semantic":false,"dim":256,"documents":0,"warning":"..."}

curl -X POST http://localhost:8000/api/embeddings/upsert \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"doc_id":"n1","text":"Lead scoring pre IT firmu na Slovensku","metadata":{"text":"Lead scoring pre IT firmu na Slovensku"}}'

curl "http://localhost:8000/api/embeddings/search?q=IT%20firma&top_k=3" \
  -H "Authorization: Bearer $TOK"

curl -X DELETE http://localhost:8000/api/embeddings/n1 -H "Authorization: Bearer $TOK"
```

> `upsert` je **idempotentný** — rovnaký `doc_id` sa nahradí, nie zduplikuje.
> Na `?q=` v `search` sa používa `metadata.text`; bez neho sa dokument nedá
> použiť ako RAG kontext.

> 🔒 Endpointy `/api/leads` a `/api/embeddings` vyžadujú JWT (`Authorization: Bearer <token>`).


### Sprint 2 — Email, sekvencie, export

**Stav Gmail/OAuth (sandbox ak nie sú poverenia)**
```bash
curl http://localhost:8000/api/email/status
# {"configured": false, "mode": "sandbox"}
```

**Odoslanie emailu (sandbox vráti simulované message_id)**
```bash
curl -X POST http://localhost:8000/api/email/send \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"to":"klient@firma.sk","subject":" Ponuka","body":"Dobrý deň ..."}'
```

**Sekvencia: vytvorenie → zapísanie leadu → spustenie**
```bash
SID=$(curl -s -X POST http://localhost:8000/api/sequences \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"name":"Onboarding","steps":[{"delay_hours":24,"subject":"Ahoj {contact_name}","body":"Vitaj {company_name}"}]}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/api/sequences/$SID/enroll \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"lead_ids":[1]}'

curl -X POST http://localhost:8000/api/sequences/$SID/run -H "Authorization: Bearer $TOK"
```

**Export: CSV (backend), Google Sheets / Docs (OAuth, sandbox fallback)**
```bash
curl http://localhost:8000/api/export/leads.csv -H "Authorization: Bearer $TOK"
curl -X POST http://localhost:8000/api/export/google-sheets \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"spreadsheet_id":"VASE_ID"}'
curl -X POST http://localhost:8000/api/export/google-docs \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"title":"Report leadov"}'
```

> 💡 **XLSX export** prebieha priamo vo frontere cez **SheetJS** (tlačidlo
> „Export XLSX“ na stránke Leads) — žiadny round-trip na server. Google
> integrácie vyžadujú OAuth poverenia (env `GMAIL_CLIENT_ID/SECRET`,
> `GOOGLE_CLIENT_ID/SECRET`); bez nich bežia v sandbox režime.

> 🔒 Endpointy `/api/email`, `/api/sequences`, `/api/export` vyžadujú JWT.

### Sprint 3 — Workflows, A/B testy, deliverability, transkripcia

**Workflow: vytvorenie a spustenie pre lead**
```bash
WF=$(curl -s -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"name":"Qualify","definition":{"steps":[{"type":"score"},{"type":"send_email","subject":"Ahoj {contact_name}","body":"Vitaj {company_name}"}]}}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/api/workflows/execute \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d "{\"workflow_id\":$WF,\"lead_id\":1}"
```

**Workflow s `wait` — pozastavenie a pokračovanie**
```bash
WF2=$(curl -s -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"name":"Nurture","definition":{"steps":[{"type":"log","message":"prvý email"},{"type":"wait","hours":72},{"type":"send_email","subject":"Follow-up","body":"Dobrý deň"}]}}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 1. beh: zastaví sa na wait, vráti status=waiting + resume_at
curl -X POST http://localhost:8000/api/workflows/execute \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d "{\"workflow_id\":$WF2,\"lead_id\":1}"

# 2. beh po uplynutí resume_at: pokračuje od kroku PO wait
curl -X POST http://localhost:8000/api/workflows/execute \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d "{\"workflow_id\":$WF2,\"lead_id\":1}"
```


**A/B sekvencia + report**
```bash
SID=$(curl -s -X POST http://localhost:8000/api/sequences \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"name":"AB","ab_enabled":true,"variants":{"A":[{"delay_hours":1,"subject":"A","body":"Variant A"}],"B":[{"delay_hours":1,"subject":"B","body":"Variant B"}]}}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -X POST http://localhost:8000/api/sequences/$SID/enroll -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" -d '{"lead_ids":[1]}'
curl http://localhost:8000/api/sequences/$SID/ab-report -H "Authorization: Bearer $TOK"
```

**Deliverability checker (SPF/DKIM/DMARC)**
```bash
curl -X POST http://localhost:8000/api/email/deliverability \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"domain":"firma.sk"}'
```

**Transkripcia + call insights**
```bash
curl -X POST http://localhost:8000/api/transcription/insights \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"transcript":"Zákazník má záujem o produkt a čaká na cenovú ponuku."}'
```

> ⚠️ **Sekvencie sa nespúšťajú automaticky.** `POST /api/sequences/{id}/run`
> treba zavolať ručne (alebo z plánovača). Celery worker je v pláne.
> Rovnako chýba **GDPR**: odhlásenie, bounce handling a suppression list.
> Pred hromadným posielaním emailov to treba doplniť.



---

## 🧪 Testovanie

```bash
cd backend && pytest          # 95 testov (mock backend, bez stahovania modelov)
cd frontend && npm run build  # TypeScript + Vite build
cd frontend && npm run lint   # ESLint
```

Rovnaké kontroly bežia automaticky v CI pri každom pushu/PR.


---

## 🗺️ Roadmapa (sprinty)

| Sprint | Výstup | Stav |
|--------|--------|------|
| **0 — Setup** | Repo scaffold, Docker Compose, FastAPI, React, README | ✅ `eca9d3d` |
| **1 — MVP core** | Auth (JWT), lead CRUD, CSV import, ORSR connector, LLM Orchestrator, embeddings | ✅ `575dab7` |
| **2** | Gmail/OAuth, sekvencie, dashboard, export | ✅ `9a1d5bb` |
| **3** | Workflow builder, A/B testy, deliverability, transkripcia | ✅ `142f3a8` |
| **4 — Stabilizácia** | Bezpečnostné guards, oprava P0 bugov, CI, `xlsx` CVE, modely mirror | ✅ táto větev |
| **5 — Produkt** | **Zdroj dát**, Celery scheduler, GDPR (unsubscribe/bounce), model `Company`/`Contact`, audit log, Tauri packaging | 📋 plánované |
| **6 — Integrácie** | CRM sync (HubSpot/Pipedrive), reporty, SSO | 📋 plánované |

Každý modul má: kód, unit + integračné testy, dokumentáciu a curl príklady.


---

## 🔐 Bezpečnosť a súkromie

**Implementované:** PBKDF2-SHA256 heslá, JWT s povinným `JWT_SECRET` mimo
development, explicitný CORS zoznam (wildcard odmietnutý), rate limit na login,
blokáda self-assign role, overenie OAuth `state` proti CSRF, tokeny s právami
`0600`, ochrana proti CSV injection, LLM cache s obmedzenou veľkosťou.

**Ešte chýba** (sľúbené v pôvodnej špecifikácii, ale neimplementované):

- Šifrovanie DB a nahrávok AES-256
- Audit log administrátorských akcií
- Právo na výmaz osobných údajov
- GDPR pre e-mail: odhlásenie, bounce, suppression list, súhlas

Podrobnosti: [`docs/deployment.md`](./docs/deployment.md) §7.


---

## 📂 Štruktúra repozitára

```
backend/        FastAPI app, služby, testy
frontend/       React + Tailwind (Tauri config pripravený, src-tauri chýba)
.github/        CI workflow (pytest + typecheck/build/lint)
infrastructure/ docker-compose, dev.env
models/         download & quantize skripty
docs/           architecture, OpenAPI spec, deployment
install.sh      jednoklikový inštalátor
```

---

## 📜 Licencia

Kód: **MIT** (pozri [`LICENSE`](./LICENSE)). Open-source modely (Mistral, Qwen,
atď.) podliehajú ich vlastným licenciám — over ich pred komerčným použitím.
