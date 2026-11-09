#!/usr/bin/env bash
# Simlink Local — installation en une commande (Linux / macOS).
# Crée un environnement virtuel, installe le moteur puis lance la configuration.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Simlink : Python 3.10 ou plus est requis (python3 introuvable ou trop ancien)." >&2
  exit 1
fi
[ -d .venv ] || "$PY" -m venv .venv
EXTRA=""
if [ "${1:-}" = "--kerbal" ]; then EXTRA="[kerbal]"; fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet ".$EXTRA"
echo "Moteur installé dans $(pwd)/.venv"
if [ -f "$HOME/.simlink/config.json" ]; then
  echo "Configuration existante conservée : $HOME/.simlink/config.json"
else
  .venv/bin/python -m simlink setup
fi
echo
echo "Étapes suivantes :"
echo "  .venv/bin/python -m simlink doctor       # lecture réelle du jeu"
echo "  .venv/bin/python -m simlink dashboard    # panneau d’approbation local"
echo "  .venv/bin/python -m simlink client-config  # bloc à coller dans votre client MCP"
