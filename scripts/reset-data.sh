#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "${CONFIRM:-}" = DELETE-LAB-DATA || { echo 'Explicit human authorization and CONFIRM=DELETE-LAB-DATA required.' >&2; exit 1; }
if kind get clusters 2>/dev/null | grep -qx laravel-reliability-lab; then echo 'Run make teardown first.' >&2; exit 1; fi
python3 - <<'PY'
from pathlib import Path
p=Path('.runtime/postgres')
assert not p.is_symlink() and p.resolve()==Path.cwd()/'.runtime/postgres','Unsafe data path'
assert Path('.env').is_file(),'No project-local credentials; refuse ambiguous reset'
PY
docker compose down --volumes
if test -d .runtime/postgres; then
 docker run --rm --user 0 --entrypoint sh -v "$PWD/.runtime/postgres:/data" postgres:18.0-bookworm -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +'
fi
echo 'Dedicated lab data reset. Credentials preserved.'
