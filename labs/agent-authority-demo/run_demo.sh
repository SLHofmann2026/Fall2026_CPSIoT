#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  exec python3 "$demo_dir/agent_authority_demo.py" run all --pause
fi

exec python3 "$demo_dir/agent_authority_demo.py" "$@"
