#!/usr/bin/env python3
"""Bounded project-only pool suspension and actual API process termination."""
from labclient import *
from experiments import interruption

def status(pod):
 p=json.loads(kube('get','pod',pod,'-o','json'))
 return {c['name']:{'ready':c['ready'],'restarts':c['restartCount'],'container_id':c['containerID']} for c in p['status']['containerStatuses']}
def local_get(pod,path,port=8082):
 code='''$ctx=stream_context_create(['http'=>['timeout'=>0.8,'ignore_errors'=>true]]);$start=microtime(true);$body=@file_get_contents('http://127.0.0.1:%d%s',false,$ctx);echo json_encode(['status'=>$http_response_header[0]??'timeout','seconds'=>microtime(true)-$start,'body'=>$body]);'''%(port,path)
 return json.loads(kube('exec',pod,'-c','api','--','php','-r',code))
def main():
 folder=ROOT/'evidence/g3'/('probes-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));folder.mkdir(parents=True)
 result={'start':utc(),'source_sha':sha(),'notes':'Intentional fault: suspend only four main-pool children for 40s; keep native status pool running. Always resume in finally. Then kill only this API container master inside the dedicated kind node; verify recovery and smoke separately.'}
 def write():(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 pod=json.loads(kube('get','pods','-l','app=api','-o','json'))['items'][0]['metadata']['name'];result['pod']=pod;result['before']=status(pod)
 code="foreach(explode(' ',trim(file_get_contents('/proc/1/task/1/children'))) as $pid) {echo $pid,':',str_replace(chr(0),' ',file_get_contents('/proc/'.$pid.'/cmdline')),PHP_EOL;}"
 children=kube('exec',pod,'-c','api','--','php','-r',code)
 result['children']=children
 pids=[int(line.split(':',1)[0]) for line in children.splitlines() if line.split(':',1)[1].strip()=='php-fpm: pool www']
 assert len(pids)==4,(children,pids)
 result['suspended_pids']=pids;result['samples']=[];write()
 try:
  kube('exec',pod,'-c','api','--','sh','-c','kill -STOP '+' '.join(map(str,pids)))
  begin=time.monotonic()
  while time.monotonic()-begin<40:
   sample={'utc':utc(),'liveness':local_get(pod,'/fpm-live'),'http':local_get(pod,'/http-live'),'main_pool_readiness':local_get(pod,'/api/ready',8080),'pod':status(pod)}
   result['samples'].append(sample);write()
   assert '200' in sample['liveness']['status'] and sample['liveness']['seconds']<.5,sample
   assert sample['pod']['api']['restarts']==result['before']['api']['restarts'],sample
   assert sample['pod']['http']['restarts']==result['before']['http']['restarts'],sample
   time.sleep(3)
 finally:kube('exec',pod,'-c','api','--','sh','-c','kill -CONT '+' '.join(map(str,pids)))
 kube('rollout','status','deployment/api','--timeout=120s')
 result['after_pool_resume']=status(pod);result['post_resume_ready']=local_get(pod,'/api/ready',8080)
 assert '200' in result['post_resume_ready']['status'],result
 assert any(not s['pod']['api']['ready'] for s in result['samples']),'Readiness failed to remove saturated pod'
 cid=result['after_pool_resume']['api']['container_id'].removeprefix('containerd://');assert len(cid)==64 and all(c in '0123456789abcdef' for c in cid)
 info=json.loads(subprocess.check_output(['docker','exec','laravel-reliability-lab-control-plane','crictl','inspect',cid],text=True));pid=int(info['info']['pid']);assert pid>1
 begin=time.monotonic();subprocess.run(['docker','exec','laravel-reliability-lab-control-plane','kill','-9',str(pid)],check=True)
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  after=status(pod)
  if after['api']['ready'] and after['api']['restarts']>result['before']['api']['restarts']:break
  time.sleep(2)
 else:raise AssertionError('Killed API process did not recover')
 result['actual_process_failure']={'after':after,'recovery_seconds':time.monotonic()-begin,'signal':'SIGKILL'}
 result['public_diagnostic_path']=local_get(pod,'/fpm-metrics',8080);assert '404' in result['public_diagnostic_path']['status']
 result['end']=utc();result['result']='PASS';write();print('PASS:',folder.relative_to(ROOT),flush=True)
if __name__=='__main__':main()
