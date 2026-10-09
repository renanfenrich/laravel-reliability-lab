from pathlib import Path
import json,os
v=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if '=' in line)
p=Path('infra/local.tfvars.json');p.write_text(json.dumps({'secrets':v}));os.chmod(p,0o600)
