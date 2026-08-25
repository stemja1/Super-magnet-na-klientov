# Modely pre lokálnu LLM inference

Tento systém beží **výhradne na lokálnych, open-source modeloch** v kvantizovanom
formáte **GGUF** cez [`llama.cpp`](https://github.com/ggerganov/llama.cpp).
Žiadna časť inference nejde do cloudu.

## Odporúčané modely (3B–7B, kvantizácia Q4_K_M / Q8_0)

| Trieda | Model (HuggingFace GGUF) | Poznámka |
|--------|--------------------------|----------|
| **7B** (predvolený) | `TheBloke/Mistral-7B-Instruct-v0.3-GGUF` (súbor `*Q4_K_M.gguf`) | Výborná multijazyčnosť, dobrá aj pre slovenčinu. |
| **7B** alternatíva | `TheBloke/OpenHermes-2.5-Mistral-7B-GGUF` | Kvalitné inštrukcie. |
| **3B** (fallback) | `TheBloke/Qwen2.5-3B-Instruct-GGUF` (`*Q4_K_M.gguf`) | Rýchlejšie, menej RAM; použi pri nedostatku pamäte. |

> Slovenský / stredoeurópsky korpus: ak je k dispozícii kvalitný slovenský
> inštruktážny model v GGUF, uprednostni ho pre lepšie výsledky v slovenskom B2B.

## Hardvérová opora (Ryzen 5600, 16 GB RAM, RX 7700 XT)

- `LLM_GPU_LAYERS=-1` odošle **všetky** vrstvy na GPU (RX 7700 XT, ~12 GB VRAM).
- Pri 7B Q4_K_M (~4.5 GB) zostáva dostatok VRAM aj pre kontext.
- Ak VRAM nestačí, nastav `LLM_GPU_LAYERS=0` (čistá CPU inference) alebo použi 3B model.

## Ako stiahnuť a kvantizovať

Použi dodaný skript (nestiahne nič bez tvojho súhlasu):

```bash
cd models
bash download_and_quantize.sh --list                 # zobrazí dostupné predvoľby
bash download_and_quantize.sh download --preset 7b  # stiahne Q4_K_M GGUF
# Voliteľne vlastná kvantizácia z f16 zdroja:
bash download_and_quantize.sh quantize path/to/model-f16.gguf Q4_K_M
```

Po stiahnutí nastav `LLM_MODEL_PATH` na cestu k `.gguf` súboru (alebo ho umiestni
do `models/gguf/` — orchestrator ho automaticky nájde).

## Inštalácia llama.cpp (Python bindings)

```bash
pip install -r backend/requirements-llm.txt
# alebo priamo:
pip install llama-cpp-python
```

Podrobnosti o kvantizácii: https://github.com/ggerganov/llama.cpp#quantization
