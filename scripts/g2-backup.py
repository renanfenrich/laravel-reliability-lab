#!/usr/bin/env python3
from labclient import *
import hashlib, uuid
run='backup-'+uuid.uuid4().hex[:10]
folder=ROOT/'evidence/g2'/run;folder.mkdir(parents=True)
private=ROOT/'.runtime/backups';private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
backup=private/(run+'.dump')
start=utc();started=time.monotonic()
sql="""SELECT json_build_object(
'reports', (SELECT json_build_object('count',count(*),'checksum',md5(coalesce(string_agg(row_to_json(t)::text,E'\\n' ORDER BY id),''))) FROM reports t),
'metrics', (SELECT json_build_object('count',count(*),'checksum',md5(coalesce(string_agg(row_to_json(t)::text,E'\\n' ORDER BY series),''))) FROM metric_samples t),
'migrations', (SELECT json_build_object('count',count(*),'checksum',md5(coalesce(string_agg(row_to_json(t)::text,E'\\n' ORDER BY id),''))) FROM migrations t));"""
def query(db,stmt):return kube('exec','deployment/postgres','--','psql','-U','lab','-d',db,'-Atqc',stmt).strip()
# Keep one exported repeatable-read snapshot alive while pg_dump and the
# expected fingerprints read exactly the same committed database state.
proc=subprocess.Popen(K+['exec','-i','deployment/postgres','--','psql','-U','lab','-d','lab','-Atq'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 proc.stdin.write('BEGIN ISOLATION LEVEL REPEATABLE READ;\nSELECT pg_export_snapshot();\n'+sql+'\n');proc.stdin.flush()
 snapshot=proc.stdout.readline().strip();assert snapshot and all(c in '0123456789ABCDEF-' for c in snapshot),snapshot
 expected=json.loads(proc.stdout.readline())
 with backup.open('wb') as out:
  os.chmod(backup,0o600)
  subprocess.run(K+['exec','deployment/postgres','--','pg_dump','-U','lab','-d','lab','--format=custom','--snapshot='+snapshot],stdout=out,check=True)
finally:
 proc.stdin.write('ROLLBACK;\n\\q\n');proc.stdin.flush();proc.wait(timeout=10)
 assert proc.returncode==0,proc.stderr.read()
dump_seconds=time.monotonic()-started
restore='g2_restore_'+uuid.uuid4().hex[:12]
assert query('postgres',"SELECT count(*) FROM pg_database WHERE datname='"+restore+"'")=='0'
kube('exec','deployment/postgres','--','createdb','-U','lab',restore)
restore_start=time.monotonic()
with backup.open('rb') as source:subprocess.run(K+['exec','-i','deployment/postgres','--','pg_restore','-U','lab','-d',restore,'--no-owner','--no-acl','--exit-on-error'],stdin=source,check=True)
actual=json.loads(query(restore,sql));assert actual==expected,(expected,actual)
row=json.loads(query(restore,"SELECT row_to_json(t) FROM (SELECT id,state,attempts,result->>'checksum' AS checksum FROM reports WHERE state='completed' ORDER BY accepted_at DESC LIMIT 1)t"));assert row['checksum'] and row['state']=='completed',row
# Application readiness against restored PostgreSQL plus existing lab Redis.
ready=kube('exec','deployment/api','--','env','DB_DATABASE='+restore,'php','artisan','lab:ready')
result={'start':start,'end':utc(),'commit':sha(),'snapshot':snapshot,'private_dump':str(backup.relative_to(ROOT)),'dump_bytes':backup.stat().st_size,'dump_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'backup_seconds':dump_seconds,'restore_seconds':time.monotonic()-restore_start,'restored_database':restore,'expected_fingerprints':expected,'restored_fingerprints':actual,'completed_result':row,'application_readiness':'PASS','result':'PASS','limitations':'Logical snapshot; isolated DB on same PostgreSQL instance. No live DB overwrite, off-host backup, PITR or arbitrary disaster proof. Private dump and restored DB retained; metrics/report fingerprints include snapshot data only.'}
(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: consistent logical backup and fresh isolated restore',folder.relative_to(ROOT),flush=True)
