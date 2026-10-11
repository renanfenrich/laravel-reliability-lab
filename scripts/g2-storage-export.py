#!/usr/bin/env python3
from labclient import *
import uuid,hashlib
run='storage-export-'+uuid.uuid4().hex[:10]
folder=ROOT/'.runtime/backups'/run;folder.mkdir(parents=True);os.chmod(folder,0o700)
evidence=ROOT/'evidence/g2'/run;evidence.mkdir(parents=True)
node='laravel-reliability-lab-control-plane'
components={'prometheus':('/prometheus',65534),'loki':('/loki',10001),'grafana':('/var/lib/grafana',472),'alertmanager':('/alertmanager',65534),'mailpit':('/data',1000),'alloy':('/alloy',1000)}
result={'start':utc(),'commit':sha(),'method':'Process-frozen crash-consistent filesystem copies; includes WAL/state. No application-consistent/off-host backup claim. Processes resumed in finally.','components':{}}
for name,(path,uid) in components.items():
 pods=json.loads(kube('get','pods','-l','app='+name,'-o','json'))['items'];assert len(pods)==1
 pod=pods[0];assert all(c['ready'] for c in pod['status']['containerStatuses']),name
 container=pod['status']['containerStatuses'][0]['containerID'].removeprefix('containerd://');assert len(container)==64 and all(c in '0123456789abcdef' for c in container)
 inspect=json.loads(subprocess.check_output(['docker','exec',node,'crictl','inspect',container],text=True));pid=int(inspect['info']['pid']);assert pid>1
 archive=folder/(name+'.tar');start=time.monotonic()
 subprocess.run(['docker','exec',node,'kill','-STOP',str(pid)],check=True)
 try:
  with archive.open('wb') as out:
   os.chmod(archive,0o600)
   subprocess.run(['docker','exec',node,'tar','--one-file-system','-C',f'/proc/{pid}/root'+path,'-cf','-','.'],stdout=out,check=True,timeout=30)
 finally:subprocess.run(['docker','exec',node,'kill','-CONT',str(pid)],check=True)
 # Materialize only this component's dedicated host directory. Keep owned
 # service data and private exports outside Git. Root is only inside a
 # disposable helper container with these two project-only bind mounts.
 destination=ROOT/'.runtime/observability'/name;destination.mkdir(parents=True,exist_ok=False)
 subprocess.run(['docker','run','--rm','--user','0','--entrypoint','sh','-v',str(destination)+':/output','-v',str(folder)+':/backup:ro','postgres:18.0-bookworm','-c',f'tar -xf /backup/{name}.tar -C /output && chown -R {uid}:{uid} /output'],check=True)
 result['components'][name]={'pod':pod['metadata']['name'],'container_id':container,'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'copy_seconds':time.monotonic()-start,'private_archive':str(archive.relative_to(ROOT)),'persistent_host_path':str(destination.relative_to(ROOT)),'uid':uid}
 print('EXPORTED',name,archive.stat().st_size,flush=True)
result['end']=utc();result['result']='PASS';(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: six private telemetry exports prepared for retained storage',evidence.relative_to(ROOT),flush=True)
