#!/usr/bin/env python3
"""Read a tunnel credential interactively; never accept it in shell history."""
from pathlib import Path
import getpass
import os
import sys

root = Path(__file__).resolve().parent.parent
assert sys.stdin.isatty(), 'Use an interactive terminal (SSH requires a TTY)'
folder = root / '.runtime/cloudflare'
assert not folder.is_symlink(), 'Credential directory must not be a symlink'
folder.mkdir(mode=0o700, parents=True, exist_ok=True)
assert folder.resolve() == root / '.runtime/cloudflare', 'Unsafe credential path'
folder.chmod(0o700)
path = folder / 'tunnel-token'
assert not path.exists(), 'Credential already exists; do not overwrite it implicitly'
token = getpass.getpass('Cloudflare Tunnel token (hidden): ').strip()
assert token and not any(c.isspace() for c in token), 'Paste only the token, not the installation command'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as handle:
    handle.write(token + '\n')
print('Saved a private ignored tunnel token; run make tunnel-up.')
