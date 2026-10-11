#!/usr/bin/env python3
"""Run the independent FPM status contract without Kubernetes or a database."""
from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parent.parent
FPM='laravel-reliability-lab-probe-check-fpm';HTTP='laravel-reliability-lab-probe-check-http'
def docker(*args):return subprocess.check_output(['docker',*args],text=True).strip()
def php(code):return docker('exec',FPM,'php','-r',code)
def get(path,port=8082):
 return json.loads(php("$c=stream_context_create(['http'=>['timeout'=>0.3,'ignore_errors'=>true]]);$b=@file_get_contents('http://127.0.0.1:%d%s',false,$c);echo json_encode(['status'=>$http_response_header[0]??'timeout','body'=>$b]);"%(port,path)))
try:
 # Do not replace existing resources bearing these names.
 existing=docker('ps','-a','--format','{{.Names}}').splitlines()
 assert FPM not in existing and HTTP not in existing,'Probe-check resources already exist; inspect ownership before cleanup'
 docker('run','-d','--name',FPM,'--label','lab.project=laravel-reliability-lab','--read-only','--tmpfs','/tmp:uid=1000,gid=1000','--cap-drop=ALL','--security-opt=no-new-privileges','laravel-reliability-app:g2')
 docker('run','-d','--name',HTTP,'--label','lab.project=laravel-reliability-lab','--network','container:'+FPM,'--user','1000:1000','--read-only','--tmpfs','/tmp:uid=1000,gid=1000','--cap-drop=ALL','--security-opt=no-new-privileges','-v',str(ROOT/'runtime/nginx-api.conf')+':/etc/lab-nginx/nginx.conf:ro','nginx:1.30.5-alpine','nginx','-c','/etc/lab-nginx/nginx.conf','-g','daemon off;')
 for _ in range(30):
  r=get('/fpm-live')
  if '200' in r['status']:break
  time.sleep(.2)
 assert json.loads(r['body'])['total processes']==4,r
 pids=json.loads(php("$p=[];foreach(explode(' ',trim(file_get_contents('/proc/1/task/1/children'))) as $pid) if(trim(str_replace(chr(0),' ',file_get_contents('/proc/'.$pid.'/cmdline'))) === 'php-fpm: pool www') $p[]=(int)$pid;echo json_encode($p);"))
 assert len(pids)==4,pids
 try:
  docker('exec',FPM,'sh','-c','kill -STOP '+' '.join(map(str,pids)))
  assert '200' in get('/fpm-live')['status']
  assert '200' in get('/http-live')['status']
  assert get('/api/live',8080)['status']=='timeout','Application pool was not actually blocked'
  assert 'phpfpm_listen_queue' in get('/fpm-metrics')['body']
  assert '404' in get('/fpm-metrics?full',8080)['status']
 finally:docker('exec',FPM,'sh','-c','kill -CONT '+' '.join(map(str,pids)))
 print('PASS: native liveness/metrics independent of all four blocked application children; diagnostic path not public')
finally:
 # Remove only containers created by this invocation, never a pre-existing name.
 for name in [HTTP,FPM]:
  if 'existing' in locals() and name not in existing:
   subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
