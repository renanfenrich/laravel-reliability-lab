#!/usr/bin/env python3
"""G2 scheduled arrivals plus bounded, sanitized PostgreSQL/pod diagnostics."""
from labclient import *
import importlib.util,threading,sys
from experiments import sql,cohort
spec=importlib.util.spec_from_file_location('g2load',ROOT/'scripts/g2-load.py')
g2=importlib.util.module_from_spec(spec);spec.loader.exec_module(g2)
WAIT_SQL="""SELECT coalesce(json_agg(t),'[]') FROM (
 SELECT CASE WHEN query ILIKE '%metric_samples%' THEN 'metrics' WHEN query ILIKE '%reports%' THEN 'reports' ELSE 'other' END AS operation,
 state,coalesce(wait_event_type,'running') AS wait_type,coalesce(wait_event,'none') AS wait_event,count(*) AS sessions,
 round(GREATEST(0,max(EXTRACT(EPOCH FROM clock_timestamp()-xact_start)))::numeric,3) AS max_transaction_seconds
 FROM pg_stat_activity WHERE datname='lab' AND pid<>pg_backend_pid() AND state<>'idle'
 GROUP BY 1,2,3,4) t"""
def pods():
 data=json.loads(kube('get','pods','-o','json'))
 return [{'pod':p['metadata']['name'],'app':p['metadata']['labels'].get('app'),
          'containers':[{'name':c['name'],'ready':c['ready'],'restarts':c['restartCount'],'state':c['state'],'last_state':c.get('lastState')} for c in p['status'].get('containerStatuses',[])]}
         for p in data['items']]
def notification_depth():
 command="REDISCLI_AUTH=\"$REDIS_PASSWORD\" redis-cli --raw EVAL 'return cjson.encode({ready=redis.call(\"LLEN\",KEYS[1]),reserved=redis.call(\"ZCARD\",KEYS[2]),delayed=redis.call(\"ZCARD\",KEYS[3])})' 3 queues:reports queues:reports:reserved queues:reports:delayed"
 return json.loads(kube('exec','deployment/redis','--','sh','-c',command))
def main(mode,goal='g3'):
 assert goal in ['g3','g4']
 assert mode in ['baseline','comparison']
 folder=ROOT/'evidence'/goal/(mode+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));folder.mkdir(parents=True)
 def write(name,value):(folder/name).write_text(json.dumps(value,indent=2)+'\n')
 result={'start':utc(),'source_sha':sha(),'mode':mode,'configuration':json.loads((ROOT/'infra/manifests.json').read_text()),'pods_before':pods(),
         'host':subprocess.check_output(['sh','-c','free -b; df -B1 .; lscpu'],text=True),'steps':[],
         'goal':goal,'notes':'Same G2 arrival generator/256 threads/15s client timeout/cohort semantics. PostgreSQL active waits sampled every 5s via bounded statement_timeout=2s; no raw SQL or identities exported. Instrumentation overhead not isolated. Local load traffic only; no 30-day attainment.'}
 write('progress.json',result);stop=threading.Event();diagnostics=[]
 def sample():
  while not stop.is_set():
   row={'utc':utc()}
   try:row['postgres']=json.loads(sql("SET statement_timeout='2s'; "+WAIT_SQL).removeprefix("SET\n"))
   except Exception as e:row['error']=type(e).__name__
   diagnostics.append(row);write('diagnostics.json',diagnostics);stop.wait(5)
 thread=threading.Thread(target=sample);thread.start()
 try:
  if goal=='g4':assert all(v==0 for v in notification_depth().values()),'Start with physically drained notification state'
  with forward('gateway',8080) as base,forward('prometheus',9090) as prom:
   for rps in ([60] if mode=='baseline' else [10,30,60]):
    print(utc(),'START',mode,rps,'rps x180s',flush=True)
    step=g2.rate(base,rps,180);write('step-'+str(rps)+'.json',step)
    result['steps'].append({k:v for k,v in step.items() if k!='samples'});result['pods_after_step']=pods();write('progress.json',result)
    print(utc(),'STEP',rps,'p99',step['client_latency_p99_seconds'],'errors',step['http_error_ratio'],'timely',step['processing_timeliness_ratio'],'generator_limited',step['generator_limited'],flush=True)
    if step['saturation_observed'] or step['generator_limited']:break
   drain=time.monotonic()+300
   while time.monotonic()<drain:
    if all(cohort(s['prefix'])['unfinished']==0 for s in result['steps']) and (goal!='g4' or all(v==0 for v in notification_depth().values())):break
    time.sleep(3)
   result['backlog_drained']=all(cohort(s['prefix'])['unfinished']==0 for s in result['steps'])
   if goal=='g4':
    result['notification_depth_before_confirmation']=notification_depth()
    assert all(v==0 for v in result['notification_depth_before_confirmation'].values()),'Notifications did not drain; confirmation unexecuted'
   result['drained_cohorts']=[cohort(s['prefix']) for s in result['steps']]
   assert result['backlog_drained'],'Backlog did not drain within 300s'
   if mode=='comparison':
    passing=[s for s in result['steps'] if not s['saturation_observed'] and not s['generator_limited'] and s['both_replicas_used']]
    assert passing,'No passing rate; confirmation not executed'
    selected=passing[-1]['offered_rate_rps'];print(utc(),'CONFIRM',selected,'rps x600s',flush=True)
    c=g2.rate(base,selected,600);write('confirmation.json',c);result['confirmation']={k:v for k,v in c.items() if k!='samples'}
    result['confirmation_passed']=not c['saturation_observed'] and not c['generator_limited'] and c['both_replicas_used']
   end=time.time();start=min(s['start_epoch'] for s in result['steps'])
   expressions={'notifications':'lab_queue_notifications','dispatch':'lab_dispatch_total','transport_failures':'lab_notification_failures_total','fpm_queue':'phpfpm_listen_queue{job="api-fpm"}','fpm_active':'phpfpm_active_processes{job="api-fpm"}','pg_waits':'lab_postgres_sessions','pg_stats':'rate(lab_postgres_stat_total[1m])','redis_queue':'lab_redis_queue_jobs','cpu':'sum by(pod,container)(rate(container_cpu_usage_seconds_total{namespace="lab",container!=""}[1m]))','throttling':'sum by(pod,container)(rate(container_cpu_cfs_throttled_seconds_total{namespace="lab",container!=""}[1m]))','memory':'sum by(pod,container)(container_memory_working_set_bytes{namespace="lab",container!=""})','reports':'lab_reports','host_cpu':'sum(rate(lab_host_cpu_seconds_total{mode!="idle"}[1m]))','host_memory':'lab_host_memory_bytes{kind="MemAvailable"}'}
   if goal=='g3':
    for name in ['notifications','transport_failures']:expressions.pop(name)
   result['resource_history']={name:g2.promquery(prom,expr,start,end) for name,expr in expressions.items()}
   result['missing_resource_history']=[name for name,values in result['resource_history'].items() if not values]
   result['pods_after']=pods();result['end']=utc();write('result.json',result)
   if goal=='g4':assert not result['missing_resource_history'],'Missing diagnostics; retain failure'
   if mode=='comparison':assert result['confirmation_passed'],'Confirmation failed; retained evidence'
 finally:
  stop.set();thread.join(timeout=10)
  events=json.loads(kube('get','events','-o','json'))
  # Event objects contain no Secret values, but only project resource events are relevant.
  write('events.json',[{'reason':e.get('reason'),'message':e.get('message'),'first':e.get('firstTimestamp'),'last':e.get('lastTimestamp'),'count':e.get('count'),'object':e.get('involvedObject',{}).get('name')} for e in events['items']])
  result['end']=utc();write('progress.json',result)
 print('EXECUTED:',folder.relative_to(ROOT),flush=True)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'comparison',sys.argv[2] if len(sys.argv)>2 else 'g3')
