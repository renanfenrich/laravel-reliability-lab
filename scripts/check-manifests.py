from pathlib import Path
import json,subprocess
p=Path('infra/manifests.json'); before=p.read_text(); subprocess.run(['python3','scripts/render-infra.py'],check=True); assert p.read_text()==before,'Regenerate manifests and commit changes'
objects=json.loads(before)
for o in objects.values():
 if o['kind']=='Deployment':
  for c in o['spec']['template']['spec']['containers']+o['spec']['template']['spec'].get('initContainers',[]):
   assert ':' in c['image'] and not c['image'].endswith(':latest')
   assert c['resources']['requests'] and c['resources']['limits']
   if c in o['spec']['template']['spec']['containers']:assert all(k in c for k in ['livenessProbe','readinessProbe','startupProbe'])
   assert c['securityContext']['allowPrivilegeEscalation'] is False
print('PASS: deterministic manifests, pinned tags, resources and probes')
