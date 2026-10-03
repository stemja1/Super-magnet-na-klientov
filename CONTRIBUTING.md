# Prispievanie

Ďakujeme za záujem. Tento projekt je lokálny Apollo.io klon pre slovenský B2B
trh — všetky príspevky sú vítané.

## Vývojové prostredie

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

Voliteľné ťažké závislosti pre reálnu lokálnu inference a sémantické vektory:

```bash
pip install -r backend/requirements-llm.txt
```

## Pred odoslaním PR

```bash
cd backend  && pytest
cd frontend && npm run build && npm run lint
```

To isté automaticky beží v CI (`.github/workflows/ci.yml`) pri každom pushu.

## Pravidlá

- **Žiadne cloudové LLM.** Inference musí ísť cez `llama.cpp`/GGUF lokálne,
  prípadne cez mock režim, ktorý musí zostať deterministický a offline.
- **Nový konektor = graceful fallback.** Každá externá integrácia má bez
  poverení či siete bežať v `sandbox` režime a nesmie spôsobiť pád aplikácie.
- **Žiadne `except: pass`.** Loguj chybu cez `logger.warning(...)` s kontextom,
  ktorý pomôže ladeniu.
- **Externé volania mimo worker threadu.** Synchronný HTTP (ORSR) v
  request handleri blokuje event loop — použi `run_in_threadpool`.
- **Bezpečnosť pred komfortom.** Nikdy neposielaj `JWT_SECRET`, klientské
  `role`, ani NeoSQL/CSV injekcii. Pridanie `?` treba odkomentovať.
- **Dokumentuj realitu.** Ak niečo nie je implementované, nech to v README
  a `docs/architecture.md` píše „plánované", nie „✅ hotové".

## Commit správy

Konvenciálne:

```
fix(sequences): izoluj zlyhanie jedného sendu v dávke
feat(embeddings): pridaj endpoint /info s informáciou o backende
docs(readme): odhaľuj, že FinStat nie je implementovaný
```

## Bezpečnostné nálezy

Nevytváraj public issue. Napíš súkromne cez GitHub Security Advisories
na stránke repozitára.
