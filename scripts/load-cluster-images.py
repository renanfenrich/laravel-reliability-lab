#!/usr/bin/env python3
"""Import only declared lab images for the documented Linux/amd64 node."""
from pathlib import Path
import json,subprocess
objects=json.loads(Path('infra/manifests.json').read_text())
images=sorted({c['image'] for o in objects.values() if o['kind']=='Deployment' for c in o['spec']['template']['spec']['containers']+o['spec']['template']['spec'].get('initContainers',[])})
for image in images:
 assert ':' in image and not image.endswith(':latest'),image
 if subprocess.run(['docker','image','inspect',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  assert not image.startswith('laravel-reliability-'),'Build missing local image first: '+image
  subprocess.run(['docker','pull','--platform','linux/amd64',image],check=True)
 save=subprocess.Popen(['docker','image','save',image],stdout=subprocess.PIPE)
 try:
  imported=subprocess.run(['docker','exec','-i','laravel-reliability-lab-control-plane','ctr','--namespace=k8s.io','images','import','--platform','linux/amd64','--digests','-'],stdin=save.stdout)
 finally:save.stdout.close()
 assert save.wait()==0 and imported.returncode==0,image
 print('IMPORTED',image,flush=True)
