#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,time
cmd=sys.argv[1:];assert cmd,'command required'
start=time.time();sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
p=Path('evidence/commands.jsonl');p.parent.mkdir(exist_ok=True)
result=subprocess.run(cmd)
with p.open('a') as f:f.write(json.dumps({'command':cmd,'start_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(start)),'end_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'duration_seconds':time.time()-start,'source_commit':sha,'exit_code':result.returncode})+'\n')
raise SystemExit(result.returncode)
