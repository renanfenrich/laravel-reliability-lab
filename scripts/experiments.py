#!/usr/bin/env python3
from labclient import *
import concurrent.futures,statistics,uuid,sys,threading

def sql(query):return kube('exec','deployment/postgres','--','psql','-U','lab','-d','lab','-Atc',query).strip()
def query_prom(base,query):return request(base,'/api/v1/query?query='+urllib.parse.quote(query),auth=False)[1]['data']['result']
def alerts(base):return request(base,'/api/v1/alerts',auth=False)[1]['data']['alerts']
def percentile(xs,p):
    xs=sorted(xs)
    if not xs:return None
    return xs[min(len(xs)-1,int((len(xs)-1)*p))]
def cohort(prefix):
    # Prefix is generated here from hex, never user SQL input.
    raw=sql("SELECT json_build_object('accepted',count(*),'completed',count(*) FILTER(WHERE state='completed'),'failed',count(*) FILTER(WHERE state='failed'),'unfinished',count(*) FILTER(WHERE state IN ('pending','processing')),'expired',count(*) FILTER(WHERE deadline_at<=now()),'deadline_met',count(*) FILTER(WHERE deadline_at<=now() AND completed_at<=deadline_at),'deadline_miss',count(*) FILTER(WHERE deadline_at<=now() AND (completed_at IS NULL OR completed_at>deadline_at)),'e2e_p99_seconds',percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM completed_at-accepted_at)) FILTER(WHERE state='completed'),'latest_deadline_seconds',GREATEST(0,EXTRACT(EPOCH FROM max(deadline_at)-now()))) FROM reports WHERE idempotency_key LIKE '"+prefix+"%'")
    return json.loads(raw)
def run_rate(base,rate,duration=20,traffic='load'):
    prefix='exp-'+uuid.uuid4().hex+'-';start=time.monotonic();started=utc();samples=[]
    def submit(i,due):
        late=max(0,time.monotonic()-due)
        try:
            code,r,latency=request(base,'/api/reports',{'subject':'synthetic-capacity'},traffic=traffic,key=prefix+str(i))
            return {'status':code,'latency_seconds':latency,'id':r.get('id'),'arrival_lateness_seconds':late}
        except Exception as e:return {'status':0,'latency_seconds':15,'error':type(e).__name__,'arrival_lateness_seconds':late}
    with concurrent.futures.ThreadPoolExecutor(max_workers=512) as pool:
        futures=[]
        for i in range(rate*duration):
            due=start+i/rate
            remaining=due-time.monotonic()
            if remaining>0:time.sleep(remaining)
            futures.append(pool.submit(submit,i,due))
        for f in futures:samples.append(f.result())
    elapsed=time.monotonic()-start;lats=[s['latency_seconds'] for s in samples];bad=sum(s['status'] not in [200,202] for s in samples)
    result={'start':started,'end_requests':utc(),'commit':sha(),'prefix':prefix,'traffic':traffic,'offered_rate_rps':rate,'offered_duration_seconds':duration,'requests':len(samples),'elapsed_client_seconds':elapsed,'throughput_rps':len(samples)/elapsed,'acceptance_rps':sum(s['status']==202 for s in samples)/elapsed,'http_error_ratio':bad/len(samples),'client_latency_p50_seconds':percentile(lats,.5),'client_latency_p95_seconds':percentile(lats,.95),'client_latency_p99_seconds':percentile(lats,.99),'client_latency_within_500ms_ratio':sum(x<=.5 for x in lats)/len(lats),'arrival_lateness_p99_seconds':percentile([s['arrival_lateness_seconds'] for s in samples],.99),'request_samples':samples}
    # Wait for ALL accepted deadlines to expire, so failures/unfinished jobs cannot vanish from timeliness.
    deadline=time.monotonic()+95
    while time.monotonic()<deadline:
        c=cohort(prefix)
        if c['accepted']==c['expired']:break
        time.sleep(3)
    result['cohort']=c
    result['processing_timeliness_ratio']=c['deadline_met']/c['expired'] if c['expired'] else None
    result['generator_limited']=result['arrival_lateness_p99_seconds']>.25
    result['end']=utc();result['saturation_observed']=bad/len(samples)>.01 or result['client_latency_within_500ms_ratio']<.99 or (result['processing_timeliness_ratio'] is not None and result['processing_timeliness_ratio']<.99)
    return result

def fault(base,payload,name):
    key='fault-'+uuid.uuid4().hex;start=time.monotonic();code,r,lat=request(base,'/api/reports',{'subject':'synthetic-'+name,**payload},traffic='fault',key=key);assert code==202,r
    result,wait=wait_report(base,r['id'],120,traffic='fault')
    return {'name':name,'report_id':r['id'],'accept_latency_seconds':lat,'completion_wait_seconds':wait,'elapsed_seconds':time.monotonic()-start,'result':result,'timestamp':utc()}

def interruption(base):
    key='fault-'+uuid.uuid4().hex;code,r,_=request(base,'/api/reports',{'subject':'synthetic-interruption','latency_ms':4000},traffic='fault',key=key);assert code==202
    id=r['id'];start=time.monotonic()
    for _ in range(80):
        _,status,_=request(base,'/api/reports/'+id,traffic='fault')
        if status['state']=='processing':break
        time.sleep(.1)
    else:raise AssertionError('Worker never claimed interruption report')
    pods=json.loads(kube('get','pods','-l','app=worker','-o','json'))['items'];victim=None
    for pod in pods:
        name=pod['metadata']['name'];logs=kube('logs',name,'--tail=200')
        if id in logs and 'report.processing' in logs:victim=name;break
    assert victim,'Cannot correlate processing worker'
    # Resolve the specific container to a process in the dedicated kind node's ancestor PID namespace.
    pod=json.loads(kube('get','pod',victim,'-o','json'))
    container=pod['status']['containerStatuses'][0]['containerID'].removeprefix('containerd://')
    assert len(container)==64 and all(c in '0123456789abcdef' for c in container)
    inspect=json.loads(subprocess.check_output(['docker','exec','laravel-reliability-lab-control-plane','crictl','inspect',container],text=True))
    pid=int(inspect['info']['pid']);assert pid>1
    subprocess.run(['docker','exec','laravel-reliability-lab-control-plane','kill','-9',str(pid)],check=True)
    result,wait=wait_report(base,id,100,traffic='fault');assert result['state']=='completed' and result['attempts']>=2,result
    return {'name':'worker-termination','report_id':id,'victim_pod':victim,'container_id':container,'killed_node_pid':pid,'result':result,'recovery_seconds':time.monotonic()-start,'wait_after_delete_seconds':wait,'timestamp':utc()}

def main(mode):
    start=utc();result={'start':start,'commit':sha(),'host':subprocess.check_output(['sh','-c','free -b; df -B1 .; lscpu'],text=True),'workload_configuration':json.loads((ROOT/'infra/manifests.json').read_text()),'notes':'Local experiments; normal/load/fault separated. No 30-day attainment claim. Python stdlib scheduled-arrival load generator equivalent; raw request samples retained.'}
    with forward('api',8080) as base,forward('prometheus',9090) as prom:
        if mode=='all':
            result['healthy_baseline']=run_rate(base,2,20,'normal');save('experiments-progress.json',result)
            result['external_latency']=fault(base,{'latency_ms':2000},'latency');assert result['external_latency']['result']['state']=='completed'
            result['external_failure']=fault(base,{'latency_ms':100,'fail_attempts':3},'failure');assert result['external_failure']['result']['state']=='failed'
            result['worker_termination']=interruption(base);save('experiments-progress.json',result)
            # Wait for accelerated demo alert, without affecting normal traffic SLO data.
            limit=time.monotonic()+110;history=[]
            while time.monotonic()<limit:
                snapshot=alerts(prom);history.append({'timestamp':utc(),'alerts':snapshot})
                if any(a['labels'].get('alertname')=='LabDemoProcessingMiss' and a['state']=='firing' for a in snapshot):break
                time.sleep(5)
            result['fault_alert_history']=history;result['fault_demo_alert_fired']=any(a['labels'].get('alertname')=='LabDemoProcessingMiss' and a['state']=='firing' for a in history[-1]['alerts']);assert result['fault_demo_alert_fired'],'Accelerated alert did not fire'
            save('experiments-progress.json',result)
        result['capacity_steps']=[]
        for rate in [2,10,30,40,50,60,120,240]:
            step=run_rate(base,rate,20);result['capacity_steps'].append(step);save('experiments-progress.json',result)
            if step['generator_limited'] or step['saturation_observed']:break
        result['saturation_observed']=any(s['saturation_observed'] and not s['generator_limited'] for s in result['capacity_steps'])
        result['generator_limited']=any(s['generator_limited'] for s in result['capacity_steps'])
        result['resource_samples']=query_prom(prom,'sum by(pod)(container_memory_working_set_bytes{namespace="lab",container!=""})')
        result['cpu_samples']=query_prom(prom,'sum by(pod)(rate(container_cpu_usage_seconds_total{namespace="lab",container!=""}[1m]))')
        result['resource_history']=request(prom,'/api/v1/query_range?query='+urllib.parse.quote('sum by(pod)(rate(container_cpu_usage_seconds_total{namespace="lab",container!=""}[1m]))')+'&start='+str(time.time()-900)+'&end='+str(time.time())+'&step=15',auth=False)[1]['data']['result']
        result['docker_resources']=subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}','laravel-reliability-lab-control-plane'],text=True)
        if mode=='all':
            limit=time.monotonic()+360;recovery=[]
            while time.monotonic()<limit:
                snapshot=alerts(prom);recovery.append({'timestamp':utc(),'alerts':snapshot})
                if not any(a['labels'].get('alertname')=='LabDemoProcessingMiss' for a in snapshot):break
                time.sleep(5)
            result['alert_recovery_history']=recovery;result['fault_demo_alert_resolved']=not any(a['labels'].get('alertname')=='LabDemoProcessingMiss' for a in recovery[-1]['alerts']);assert result['fault_demo_alert_resolved'],'Accelerated alert did not resolve within bounded cohort horizon'
    result['end']=utc();result['result']='PARTIAL' if result['generator_limited'] else 'PASS';save('experiments.json',result)
    print(result['result']+': experiment execution only; saturation observed = '+str(result['saturation_observed'])+'; no 30-day attainment claim')
    if result['generator_limited']:raise RuntimeError('Client generator limited: capacity remains unestablished for this run')
if __name__=='__main__':
    import urllib.parse
    try:main(sys.argv[1] if len(sys.argv)>1 else 'all')
    except Exception as e:save('experiment-error.json',{'timestamp':utc(),'commit':sha(),'error':type(e).__name__,'message':str(e)});raise
