#!/usr/bin/env python3
from labclient import *
from experiments import cohort,percentile
from collections import Counter
import concurrent.futures,uuid,urllib.parse,sys
def write(name,data):(folder/name).write_text(json.dumps(data,indent=2)+'\n')
def promquery(base,expr,start,end):
 path='/api/v1/query_range?query='+urllib.parse.quote(expr)+'&start='+str(start)+'&end='+str(end)+'&step=15'
 return request(base,path,auth=False)[1]['data']['result']
def rate(base,rps,seconds):
 prefix='g2-load-'+uuid.uuid4().hex+'-';start=time.monotonic();epoch=time.time();samples=[]
 def submit(i,due):
  late=max(0,time.monotonic()-due);begin=time.monotonic()
  req=urllib.request.Request(base+'/api/reports',data=json.dumps({'subject':'synthetic-g2-load'}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+ENV['LAB_TOKEN'],'X-Lab-Traffic':'load','Idempotency-Key':prefix+str(i)})
  try:
   with urllib.request.urlopen(req,timeout=15) as response:
    payload=json.load(response)
    return {'status':response.status,'latency_seconds':time.monotonic()-begin,'arrival_lateness_seconds':late,'id':payload.get('id'),'api_pod':response.headers.get('X-Lab-API-Pod')}
  except urllib.error.HTTPError as error:return {'status':error.code,'latency_seconds':time.monotonic()-begin,'arrival_lateness_seconds':late,'error':'HTTPError'}
  except Exception as error:return {'status':0,'latency_seconds':time.monotonic()-begin,'arrival_lateness_seconds':late,'error':type(error).__name__}
 with concurrent.futures.ThreadPoolExecutor(max_workers=256) as pool:
  futures=[]
  for i in range(rps*seconds):
   due=start+i/rps;remaining=due-time.monotonic()
   if remaining>0:time.sleep(remaining)
   futures.append(pool.submit(submit,i,due))
  samples=[f.result() for f in futures]
 elapsed=time.monotonic()-start;end_requests=time.time();lats=[s['latency_seconds'] for s in samples];bad=sum(s['status']!=202 for s in samples)
 deadline=time.monotonic()+95
 while time.monotonic()<deadline:
  c=cohort(prefix)
  if c['accepted']==c['expired']:break
  time.sleep(3)
 assert c['accepted']==c['expired'],'Unexpired accepted cohort; test cannot claim timeliness'
 timely=c['deadline_met']/c['expired'] if c['expired'] else None
 distribution=Counter(s.get('api_pod') for s in samples if s.get('api_pod'))
 result={'start_epoch':epoch,'end_requests_epoch':end_requests,'end_epoch':time.time(),'commit':sha(),'prefix':prefix,'traffic':'load','offered_rate_rps':rps,'duration_seconds':seconds,'requests':len(samples),'elapsed_client_seconds':elapsed,'response_throughput_rps':len(samples)/elapsed,'accepted_throughput_rps':sum(s['status']==202 for s in samples)/elapsed,'http_error_ratio':bad/len(samples),'client_latency_p50_seconds':percentile(lats,.5),'client_latency_p95_seconds':percentile(lats,.95),'client_latency_p99_seconds':percentile(lats,.99),'client_latency_within_500ms_ratio':sum(x<=.5 for x in lats)/len(lats),'arrival_lateness_p99_seconds':percentile([s['arrival_lateness_seconds'] for s in samples],.99),'serving_api_pods':dict(distribution),'cohort':c,'processing_timeliness_ratio':timely,'samples':samples}
 result['generator_limited']=result['arrival_lateness_p99_seconds']>.25
 result['saturation_observed']=result['http_error_ratio']>.01 or result['client_latency_within_500ms_ratio']<.99 or timely is None or timely<.99
 result['both_replicas_used']=len(distribution)==2
 return result
def main():
 run='load-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
 global folder
 folder=ROOT/'evidence/g2'/run;folder.mkdir(parents=True)
 result={'start':utc(),'commit':sha(),'notes':'G2 local scheduled-arrival load through gateway and API Service, no upstream automatic retries. 180-second steps plus a 600-second confirmation; not production capacity/30-day compliance. Private runtime credentials excluded.','steps':[],'configuration':json.loads((ROOT/'infra/manifests.json').read_text()),'host':subprocess.check_output(['sh','-c','free -b; df -B1 .; lscpu'],text=True)}
 write('progress.json',result)
 with forward('gateway',8080) as base,forward('prometheus',9090) as prom:
  for rps in [10,30,60,90,120,180,240]:
   print(utc(),'START',rps,'rps x180s',flush=True)
   step=rate(base,rps,180);write('step-'+str(rps)+'.json',step)
   result['steps'].append({k:v for k,v in step.items() if k!='samples'})
   print(utc(),'STEP',rps,'p99',round(step['client_latency_p99_seconds'],4),'errors',step['http_error_ratio'],'timely',step['processing_timeliness_ratio'],'pods',step['serving_api_pods'],'generator_limited',step['generator_limited'],flush=True)
   write('progress.json',result)
   if step['saturation_observed'] or step['generator_limited']:break
  passing=[s for s in result['steps'] if not s['saturation_observed'] and not s['generator_limited'] and s['both_replicas_used']]
  assert passing,'No passing offered rate; preserve failure and investigate'
  selected=passing[-1]['offered_rate_rps']
  # Do not start a confirmation while a saturated cohort still has work.
  drain=time.monotonic()+180
  while time.monotonic()<drain:
   if all(cohort(s['prefix'])['unfinished']==0 for s in result['steps']):break
   time.sleep(3)
  assert all(cohort(s['prefix'])['unfinished']==0 for s in result['steps']),'Saturated backlog did not drain; confirmation unexecuted'
  print(utc(),'CONFIRM',selected,'rps x600s',flush=True)
  confirmation=rate(base,selected,600);write('confirmation.json',confirmation)
  result['confirmation']={k:v for k,v in confirmation.items() if k!='samples'}
  end=time.time();start=min(s['start_epoch'] for s in result['steps'])
  expressions={'cpu':'sum by(pod)(rate(container_cpu_usage_seconds_total{namespace="lab",container!=""}[1m]))','memory':'sum by(pod)(container_memory_working_set_bytes{namespace="lab",container!=""})','throttling':'sum by(pod)(rate(container_cpu_cfs_throttled_seconds_total{namespace="lab",container!=""}[1m]))','reports':'lab_reports','host_cpu':'sum(rate(lab_host_cpu_seconds_total{mode!="idle"}[1m]))','host_memory':'lab_host_memory_bytes{kind="MemAvailable"}'}
  result['resource_history']={name:promquery(prom,expr,start,end) for name,expr in expressions.items()}
  result['end']=utc();result['result']='PASS' if not confirmation['saturation_observed'] and not confirmation['generator_limited'] and confirmation['both_replicas_used'] else 'FAIL'
  result['saturation_observed']=any(s['saturation_observed'] and not s['generator_limited'] for s in result['steps'])
  write('result.json',result)
  assert result['result']=='PASS',result['confirmation']
 print('PASS: sustained capacity experiment',folder.relative_to(ROOT),flush=True)
if __name__=='__main__':main()
