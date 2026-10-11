#!/usr/bin/env python3
from labclient import *
from experiments import run_rate
import concurrent.futures,uuid
run='interruption-'+uuid.uuid4().hex[:10];folder=ROOT/'evidence/g2'/run;folder.mkdir(parents=True)
def write(name,data):(folder/name).write_text(json.dumps(data,indent=2)+'\n')
start=utc();node='laravel-reliability-lab-control-plane'
def completed_count():
 query='''SELECT COALESCE((SELECT value FROM metric_samples WHERE series='lab_completed_total{traffic="fault"}'),0)'''
 return float(kube('exec','deployment/postgres','--','psql','-U','lab','-d','lab','-Atc',query).strip())
completed_before=completed_count()
with forward('gateway',8080) as base:
 # A small concurrent, separate load cohort demonstrates recovery while
 # HTTP submissions continue; it is not mixed into normal SLO traffic.
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  background=pool.submit(run_rate,base,10,60,'load')
  def submit(i):
   code,r,_=request(base,'/api/reports',{'subject':'synthetic-g2-interruption','latency_ms':4000},traffic='fault',key='g2-kill-'+run+'-'+str(i));assert code==202,r;return r['id']
  ids=list(pool.map(submit,range(2)))
  deadline=time.monotonic()+30;victims={}
  while time.monotonic()<deadline:
   states={id:request(base,'/api/reports/'+id,traffic='fault')[1] for id in ids}
   if all(r['state']=='processing' and r['attempts']==1 for r in states.values()):
    pods=json.loads(kube('get','pods','-l','app=worker','-o','json'))['items']
    for pod in pods:
     name=pod['metadata']['name'];logs=kube('logs',name,'--tail=100')
     matches=[id for id in ids if any(id in line and 'report.processing' in line for line in logs.splitlines())]
     if len(matches)==1:
      container=pod['status']['containerStatuses'][0]['containerID'].removeprefix('containerd://');assert len(container)==64 and all(c in '0123456789abcdef' for c in container)
      inspect=json.loads(subprocess.check_output(['docker','exec',node,'crictl','inspect',container],text=True));pid=int(inspect['info']['pid']);assert pid>1
      victims[matches[0]]={'pod':name,'container':container,'node_pid':pid,'before_log':logs,'before_state':states[matches[0]]}
    if len(victims)==2 and len({v['pod'] for v in victims.values()})==2:break
   time.sleep(.05)
  assert len(victims)==2 and len({v['pod'] for v in victims.values()})==2,'Two active workers were not correlated before termination'
  # Recheck leases immediately before killing; reject a completed job.
  assert all(request(base,'/api/reports/'+id,traffic='fault')[1]['state']=='processing' for id in ids)
  write('before-kill.json',{'start':start,'commit':sha(),'ids':ids,'victims':victims})
  killed=utc();killed_epoch=time.monotonic()
  subprocess.run(['docker','exec',node,'kill','-9',*[str(v['node_pid']) for v in victims.values()]],check=True)
  print(killed,'KILLED both correlated worker processes',flush=True)
  recovered={}
  for id in ids:
   result,_=wait_report(base,id,100,traffic='fault');assert result['state']=='completed' and result['attempts']==2 and result['result']['checksum'],result
   row=kube('exec','deployment/postgres','--','psql','-U','lab','-d','lab','-Atc',f"SELECT count(*),max(attempts),max(result->>'checksum') FROM reports WHERE id='{id}' AND state='completed'").strip();assert row.startswith('1|2|'),row
   recovered[id]={'result':result,'row':row,'observed_recovery_seconds':time.monotonic()-killed_epoch}
  completed_after=completed_count();assert completed_after-completed_before==2,(completed_before,completed_after)
  load=background.result();write('background-load.json',load)
  assert not load['generator_limited'] and not load['saturation_observed'],load
  write('result.json',{'start':start,'end':utc(),'commit':sha(),'kill_timestamp':killed,'fault_completed_counter_delta':completed_after-completed_before,'recovered':recovered,'background_load':{k:v for k,v in load.items() if k!='request_samples'},'result':'PASS','limitations':'Two correlated SIGKILL events under one bounded 10rps/60s load cohort. No arbitrary node/database failure or production recovery probability claim.'})
print('PASS: both interrupted reports completed on attempt2 with one result under concurrent load',folder.relative_to(ROOT),flush=True)
