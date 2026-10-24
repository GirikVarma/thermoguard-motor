#!/bin/zsh
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 server.py
elif [[ -x .venv/bin/python ]]; then
  .venv/bin/python server.py
else
  open ThermoGuard_Standalone.html
fi
