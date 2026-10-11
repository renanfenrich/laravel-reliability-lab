#!/usr/bin/env python3
"""Bounded live-lab worker pause; only sanitized synthetic report multiplicities."""
from labclient import *
from experiments import sql
import uuid,collections,sys,re

def redis(command):
 return kube('exec','deployment/redis','--','sh','-c','REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --raw '+command).strip()
def depth():return {'ready':int(redis('LLEN queues:reports')),'reserved':int(redis('ZCARD queues:reports:reserved')),'delayed':int(redis('ZCARD queues:reports:delayed'))}
def main(stage):
 assert stage in ['before','after']
 folder=ROOT/'evidence/g4'/('pause-'+stage+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));folder.mkdir(parents=True)
 result={'start':utc(),'source_sha':sha(),'stage':stage,'samples':[],'notes':'Pause project workers for 30s, submit 20 synthetic fault reports, inspect at most 500 waiting payloads in memory only; export report multiplicities and queue counts, never raw payloads. Restore original replica count in finally.'}
 def write():(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 replicas=json.loads(kube('get','deployment/worker','-o','json'))['spec']['replicas'];assert replicas==2,replicas
 assert all(v==0 for v in depth().values()),'Notification queue must be quiescent before pause'
 assert sql("SELECT count(*) FROM reports WHERE state IN ('pending','processing')")=='0','Accepted work must be drained before pause'
 result['original_worker_replicas']=replicas;write()
 try:
  kube('scale','deployment/worker','--replicas=0');kube('wait','--for=delete','pod','-l','app=worker','--timeout=90s')
  with forward('gateway',8080) as base:
   result['reports']=[]
   for i in range(20):
    code,r,_=request(base,'/api/reports',{'subject':'synthetic-g4-pause'},traffic='fault',key='g4-pause-'+uuid.uuid4().hex)
    assert code==202,(code,r);result['reports'].append(r['id'])
   write();begin=time.monotonic()
   while time.monotonic()-begin<30:
    counts=depth();assert counts['ready']<=500,'Bounded queue inspection exceeded; restore workers and retain failure'
    payloads=redis('LRANGE queues:reports 0 499').splitlines()
    multiplicity={id:sum(id in p for p in payloads) for id in result['reports']}
    sample={'utc':utc(),'queue':counts,'per_report_multiplicity':multiplicity};result['samples'].append(sample);write();time.sleep(5)
 finally:
  kube('scale','deployment/worker','--replicas='+str(replicas));kube('rollout','status','deployment/worker','--timeout=120s')
 result['restored']=utc();write()
 with forward('gateway',8080) as base:
  result['completed']={id:wait_report(base,id,90,traffic='fault')[0] for id in result['reports']}
  assert all(r['state']=='completed' and r['attempts']==1 for r in result['completed'].values()),result['completed']
 end=time.monotonic()+90
 while time.monotonic()<end:
  if all(v==0 for v in depth().values()):break
  time.sleep(3)
 result['queue_after']=depth();result['end']=utc();result['max_multiplicity']=max(n for s in result['samples'] for n in s['per_report_multiplicity'].values())
 result['result']='PASS' if all(v==0 for v in result['queue_after'].values()) and (stage=='before' and result['max_multiplicity']>1 or stage=='after' and result['max_multiplicity']==1) else 'FAIL'
 write();assert result['result']=='PASS',result
 print('PASS:',stage,'multiplicity',result['max_multiplicity'],folder.relative_to(ROOT),flush=True)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'after')
