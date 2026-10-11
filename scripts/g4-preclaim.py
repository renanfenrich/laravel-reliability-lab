#!/usr/bin/env python3
"""Kill an owned PHP consumer immediately after native reservation, before handle."""
from labclient import *
from experiments import sql
import importlib.util,uuid
spec=importlib.util.spec_from_file_location('pause',ROOT/'scripts/g4-pause.py');pause=importlib.util.module_from_spec(spec);spec.loader.exec_module(pause)
def main():
 folder=ROOT/'evidence/g4'/('preclaim-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));folder.mkdir(parents=True)
 result={'start':utc(),'source_sha':sha(),'notes':'Quiescent project worker pause; API acceptance creates one fault report. An owned ephemeral PHP CLI consumer in an API pod reserves that notification then SIGKILLs itself before handle. Restore original workers in finally; no live Redis deletion or API master termination.'}
 def write():(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 assert all(v==0 for v in pause.depth().values())
 assert sql("SELECT count(*) FROM reports WHERE state IN ('pending','processing')")=='0'
 replicas=json.loads(kube('get','deployment/worker','-o','json'))['spec']['replicas'];assert replicas==2
 before=float(sql("SELECT coalesce((SELECT value FROM metric_samples WHERE series='lab_notification_failures_total'),0)"))
 try:
  kube('scale','deployment/worker','--replicas=0');kube('wait','--for=delete','pod','-l','app=worker','--timeout=90s')
  with forward('gateway',8080) as base:
   code,r,_=request(base,'/api/reports',{'subject':'synthetic-g4-preclaim'},traffic='fault',key='g4-preclaim-'+uuid.uuid4().hex);assert code==202
   id=r['id'];uuid.UUID(id);result['report_id']=id;write()
  pod=json.loads(kube('get','pods','-l','app=api','-o','json'))['items'][0]['metadata']['name']
  code="require '/app/vendor/autoload.php';$app=require '/app/bootstrap/app.php';$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();$job=app('queue')->connection('redis')->pop('reports');if(!$job || ($job->payload()['report_id']??null)!=='"+id+"'){if($job)$job->release(0);exit(2);}echo json_encode(['report_id'=>$job->payload()['report_id'],'attempts'=>$job->attempts(),'pid'=>getmypid()]),PHP_EOL;posix_kill(getmypid(),9);"
  killed=time.monotonic();execution=subprocess.run(K+['exec',pod,'-c','api','--','php','-r',code],capture_output=True,text=True,timeout=15)
  result['consumer_exit']={'code':execution.returncode,'stdout':execution.stdout,'stderr':execution.stderr};assert execution.returncode==137,execution
  result['after_reservation']={'state':sql("SELECT state||'|'||attempts FROM reports WHERE id='"+id+"'"),'notifications':pause.depth()};assert result['after_reservation']['state']=='pending|0';write()
 finally:
  kube('scale','deployment/worker','--replicas='+str(replicas));kube('rollout','status','deployment/worker','--timeout=120s')
 with forward('gateway',8080) as base:
  done,_=wait_report(base,id,100,traffic='fault');assert done['state']=='completed' and done['attempts']==1,done
  result['report']=done;result['recovery_seconds']=time.monotonic()-killed
 after=float(sql("SELECT value FROM metric_samples WHERE series='lab_notification_failures_total'"));result['transport_failure_delta']=after-before;assert result['transport_failure_delta']==1
 result['guard_exists']=int(pause.redis('EXISTS lab:notification:queues:reports:'+id));assert result['guard_exists']==0
 limit=time.monotonic()+30
 while time.monotonic()<limit:
  if all(v==0 for v in pause.depth().values()):break
  time.sleep(2)
 result['queue_after']=pause.depth();assert all(v==0 for v in result['queue_after'].values())
 result['end']=utc();result['result']='PASS';write();print('PASS: preclaim SIGKILL and native exhaustion recovered',folder.relative_to(ROOT),flush=True)
if __name__=='__main__':main()
