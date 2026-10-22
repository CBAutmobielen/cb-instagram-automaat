#!/usr/bin/env bash
# Rendert alle actieve auto's en controleert daarna het resultaat.
# Optioneel eerst het aanbod verversen:  bash run.sh --fetch
set -e
cd "$(dirname "$0")"
if [ "$1" == "--fetch" ]; then python cb/fetch.py; fi
python cb/render.py
python cb/verify.py
