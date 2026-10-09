from pathlib import Path
import subprocess
v=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if '=' in line)
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],text=True).split('\0');hits=[]
for name in files:
 p=Path(name)
 if p.is_file() and any(v[k].encode() in p.read_bytes() for k in ['APP_KEY','DB_PASSWORD','REDIS_PASSWORD','LAB_TOKEN']):hits.append(name)
assert not hits,'Runtime credentials found in candidate tracked files: '+','.join(hits)
subprocess.run(['docker','run','--rm','laravel-reliability-app:g1','sh','-c','test ! -e /app/.env && test ! -e /app/infra && test ! -e /app/.tools'],check=True)
print('PASS: actual runtime credentials excluded from Git candidates and private files excluded from final image')
