#!/usr/bin/env bash
# =============================================================================
# download_and_quantize.sh
# Stiahne a/alebo kvantizuje lokálne LLM modely (GGUF) pre llama.cpp.
#
# CIEĽ: žiadne cloudové LLM závislosti. Všetka inference prebieha lokálne.
# BEZPEČNOSŤ: skript NIČ nestiahne bez výslovného prepínača (--download),
#            aby sa pri inštalácii neťahali veľké súbory automaticky.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GGUF_DIR="${GGUF_DIR:-$SCRIPT_DIR/gguf}"
HF="${HF_CLI:-hf}"   # 'hf' (huggingface_hub CLI) alebo 'curl'

mkdir -p "$GGUF_DIR"

# ---- Predvoľby modelov (repo + názov GGUF súboru) --------------------------
# POZOR: pôvodné repozitáre TheBloke/* boli z HuggingFace odstránené (HTTP 401).
# Používaj komunitné mirror-y, ktoré stále existujú.
declare -A PRESET_REPO=(
  ["7b"]="bartowski/Mistral-7B-Instruct-v0.3-GGUF"
  ["3b"]="bartowski/Qwen2.5-3B-Instruct-GGUF"
  ["7b-oh"]="TheBloke/OpenHermes-2.5-Mistral-7B-GGUF"
)
declare -A PRESET_FILE=(
  ["7b"]="Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
  ["3b"]="Qwen2.5-3B-Instruct-Q4_K_M.gguf"
  ["7b-oh"]="openhermes-2.5-mistral-7b.Q4_K_M.gguf"
)

usage() {
  cat <<'EOF'
Použitie:
  download_and_quantize.sh --list
  download_and_quantize.sh download --preset <7b|3b|7b-oh>
  download_and_quantize.sh quantize <cesta/f16.gguf> <Q4_K_M|Q8_0|...>
  download_and_quantize.sh --help

Predvoľby:
  7b     Mistral-7B-Instruct v0.3 (Q4_K_M)   — predvolený, dobrá multijazyčnosť
  3b     Qwen2.5-3B-Instruct (Q4_K_M)        — fallback pri nedostatku pamäte
  7b-oh  OpenHermes-2.5-Mistral-7B (Q4_K_M)  — kvalitné inštrukcie
EOF
}

list_presets() {
  echo "Dostupné predvoľby:"
  for k in "${!PRESET_REPO[@]}"; do
    printf "  %-6s -> %s  (%s)\n" "$k" "${PRESET_REPO[$k]}" "${PRESET_FILE[$k]}"
  done
}

cmd_list() { list_presets; }

cmd_download() {
  local preset="$1"
  local repo="${PRESET_REPO[$preset]:-}"
  local file="${PRESET_FILE[$preset]:-}"
  if [[ -z "$repo" || -z "$file" ]]; then
    echo "Neznáma predvoľba: $preset" >&2
    list_presets
    exit 1
  fi
  local out="$GGUF_DIR/$file"
  # Pred stiahnutím veľkého súboru over, že repozitár naozaj existuje —
  # TheBloke repozitáre boli odstránené a download by ticho zlyhal.
  if command -v curl >/dev/null 2>&1; then
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' "https://huggingface.co/api/models/$repo")"
    if [[ "$code" != "200" ]]; then
      echo "CHYBA: repozitár '$repo' nie je dostupný (HTTP $code)." >&2
      echo "Hľadaj mirror na https://huggingface.co/models?search=gguf" >&2
      exit 1
    fi
  fi
  echo "Sťahujem $repo / $file -> $out"
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$repo" "$file" --local-dir "$GGUF_DIR" --local-dir-use-symlinks False
  else
    # Priamy download cez HuggingFace CDN (vyžaduje curl).
    local url="https://huggingface.co/$repo/resolve/main/$file"
    echo "Používam curl: $url"
    curl -L --progress-bar -o "$out" "$url"
  fi
  echo "Hotovo. Nastav LLM_MODEL_PATH=$out (alebo ho nechaj v $GGUF_DIR)."
}

cmd_quantize() {
  local src="$1" qtype="${2:-Q4_K_M}"
  if [[ ! -f "$src" ]]; then echo "Zdrojový model neexistuje: $src" >&2; exit 1; fi
  # llama.cpp quantize nástroj musí byť zostavený (alebo nainštalovaný cez pip).
  if command -v llama-quantize >/dev/null 2>&1; then
    local out="${src%.gguf}-${qtype}.gguf"
    llama-quantize "$src" "$out" "$qtype"
    echo "Skvantizované -> $out"
  else
    echo "Nenájdený 'llama-quantize'. Zostav llama.cpp alebo nainštaluj:" >&2
    echo "  pip install llama-cpp-python  (obsahuje quantize utility)" >&2
    exit 1
  fi
}

# ---- CLI parsing -----------------------------------------------------------
if [[ $# -eq 0 ]]; then usage; exit 0; fi
case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --list)    cmd_list; exit 0 ;;
  download)
    shift
    PRESET="7b"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --preset) PRESET="${2:-7b}"; shift 2 ;;
        *) echo "Neznámy argument: $1" >&2; exit 1 ;;
      esac
    done
    cmd_download "$PRESET"
    ;;
  quantize)
    shift
    cmd_quantize "${1:-}" "${2:-Q4_K_M}"
    ;;
  *)
    echo "Neznámy príkaz: $1" >&2
    usage
    exit 1
    ;;
esac
