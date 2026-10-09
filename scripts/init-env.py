#!/usr/bin/env python3
from pathlib import Path
import secrets,base64,os
p=Path('.env')
if not p.exists():
    p.write_text('APP_ENV=local\nAPP_KEY=base64:'+base64.b64encode(secrets.token_bytes(32)).decode()+'\nDB_PASSWORD='+secrets.token_hex(24)+'\nREDIS_PASSWORD='+secrets.token_hex(24)+'\nLAB_TOKEN='+secrets.token_hex(24)+'\nLAB_FAULTS=true\n')
    os.chmod(p,0o600)
