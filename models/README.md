# Modely pre lokálnu LLM inference

Tento systém beží **výhradne na lokálnych, open-source modeloch** v kvantizovanom
formáte **GGUF** cez [llama.cpp](https://github.com/ggerganov/llama.cpp).
Žiadna časť inference nejde do cloudu.

> ⚠️ **Pozor na zdroje modelov.** Predvolené repozitáre `TheBloke/*` boli zo
> HuggingFace odstránené a stiahnutie z nich vracia `401`. Používaj preto
> komunitné mirror-y (nižšie). Ak `install.sh` ponúkne stiahnutie modelu,
> najprv si ho over.

## Odporúčané modely (3B–7B, kvantizácia Q4_K_M)

| Trieda | Model (HuggingFace GGUF) | Súbor | Poznámka |
|--------|--------------------------|--------|----------|
| **7B** (predvolený) | `bartowski/Mistral-7B-Instruct-v0.3-GGUF` | `Mistral-7B-Instruct-v0.3-Q4_K_M.gguf` | Dobrá viacjazyčnosť, zvládne slovenčinu. |
| **7B** alternatíva | `TheBloke/OpenHermes-2.5-Mistral-7B-GGUF` | `openhermes-2.5-mistral-7b.Q4_K_M.gguf` | Kvalitnejšie inštrukcie. |
| **3B** (fallback) | `bartowski/Qwen2.5-3B-Instruct-GGUF` | `Qwen2.5-3B-Instruct-Q4_K_M.gguf` | Rýchlejší, menej RAM; použi pri nedostatku pamäte. |

> Slovenský / stredoeurópsky korpus: ak je k dispozícii kvalitný slovenský
> inštrukčný model v GGUF, uprednostni ho pre lepšie výsledky v slovenskom B2B.

## Hardvérová opora (Ryzen 5600, 16 GB RAM, RX 7700 XT)

- `LLM_GPU_LAYERS=-1` odloží **všetky** vrstvy na GPU (RX 7700 XT, ~12 GB VRAM).
- Pri 7B Q4_K_M (~4.5 GB) zostáva dostatok VRAM aj pre kontext.
- Ak VRAM nestačí, nastav `LLM_GPU_LAYERS=0` (čistý CPU inference) alebo použi 3B model.

## Ako stiahnuť a kvantizovať

Použi dodaný skript (nestiahne nič bez tvojho súhlasu):

```bash
cd models
bash download_and_quantize.sh --list                 # zobrazí dostupné predvoľby
bash download_and_quantize.sh download --preset 7b   # stiahne Q4_K_M GGUF
# Voliteľná vlastná kvantizácia z f16 zdroja:
bash download_and_quantize.sh quantize path/to/model-f16.gguf Q4_K_M
```

Po stiahnutí nastav `LLM_MODEL_PATH` na cestu k `.gguf` súboru (alebo ho nechaj
v `models/gguf/` — orchestrator ho nájde automaticky).

Overenie dostupnosti pred stiahnutím veľkého súboru:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://huggingface.co/api/models/bartowski/Mistral-7B-Instruct-v0.3-GGUF   # očakávané 200
```

## Inštalácia llama.cpp (Python bindings)

```bash
pip install -r backend/requirements-llm.txt
# alebo priamo:
pip install llama-cpp-python
```

Podrobnosti o kvantizácii: https://github.com/ggerganov/llama.cpp#quantization
