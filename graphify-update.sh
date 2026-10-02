#!/usr/bin/env bash
# Atualiza o grafo do graphify. Extração estrutural (AST), sem LLM e sem Obsidian.
#
# Uso:
#   ./graphify-update.sh              # update estrutural (sem LLM)
#   ./graphify-update.sh --force      # update mesmo se o grafo encolher
#   ./graphify-update.sh --no-cluster # só re-extrai código (sem clustering)
#
# EXPLÍCITO (intencional neste projeto):
#   - NÃO exporta vault para Obsidian (não existe export de vault aqui).
#   - NÃO usa extração semântica / LLM (zero custo de tokens, zero API keys).
#   - Gera apenas o necessário para a skill do graphify ler os arquivos:
#     graphify-out/graph.json + graphify-out/GRAPH_REPORT.md (+ graph.html).
#
# Requisitos:
#   - graphify instalado (uv tool install graphifyy) OU usar --python <interp>

set -euo pipefail

# Raiz do projeto = diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GRAPHIFY_OUT="graphify-out"

# ---- Resolve o interpretador Python do graphify ----
PYTHON=""
if [ -f "$GRAPHIFY_OUT/.graphify_python" ]; then
  PYTHON="$(cat "$GRAPHIFY_OUT/.graphify_python")"
fi
if [ -z "$PYTHON" ] || ! "$PYTHON" -c "import graphify" >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1; then
    PYTHON="$(uv tool run --from graphifyy python -c "import sys; print(sys.executable)" 2>/dev/null || true)"
  fi
fi
if [ -z "$PYTHON" ]; then
  PYTHON="$(command -v graphify >/dev/null 2>&1 && head -1 "$(command -v graphify)" | tr -d '#!' || echo python3)"
fi
if ! "$PYTHON" -c "import graphify" >/dev/null 2>&1; then
  echo "erro: graphify não está instalado (pip install 'graphifyy' ou uv tool install graphifyy)." >&2
  exit 1
fi
mkdir -p "$GRAPHIFY_OUT"
echo "$PYTHON" > "$GRAPHIFY_OUT/.graphify_python"

# ---- Update estrutural (AST, sem LLM) ----
echo "==> graphify update (estrutural, SEM LLM, SEM Obsidian)"
if ! "$PYTHON" -m graphify update . "$@"; then
  echo "erro: update do graphify falhou." >&2
  exit 1
fi

echo
echo "OK. Grafo atualizado (sem LLM, sem export Obsidian)."
echo "Saída: $GRAPHIFY_OUT/graph.json + $GRAPHIFY_OUT/GRAPH_REPORT.md"
