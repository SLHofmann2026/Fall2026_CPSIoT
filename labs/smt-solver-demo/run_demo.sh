#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v z3 >/dev/null 2>&1; then
  echo "z3 was not found on PATH." >&2
  echo "Install Z3 or add its binary to PATH, then run this script again." >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  exec python3 "$demo_dir/cps_sat_demo.py" all --pause
fi

exec python3 "$demo_dir/cps_sat_demo.py" "$@"
