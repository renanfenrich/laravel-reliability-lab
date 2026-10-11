#!/usr/bin/env python3
from labclient import *
import sys
names=['prometheus','loki','grafana','alertmanager','mailpit','alloy'];start=utc()
def pods():
 items=json.loads(kube('get','pods','-l','app in ('+','.join(names)+')','-o','json'))['items']
 return {p['metadata']['name']:p for p in items}
before=pods();assert len(before)==6 and all(all(c['ready'] for c in p['status']['containerStatuses']) for p in before.values())
kube('delete','pod',*before.keys(),'--wait=true','--timeout=90s')
end=time.monotonic()+180
while time.monotonic()<end:
 after=pods()
 if len(after)==6 and not set(after).intersection(before) and all(p['status'].get('containerStatuses') and all(c['ready'] for c in p['status']['containerStatuses']) for p in after.values()):break
 time.sleep(3)
else:raise AssertionError('Telemetry replacement pods did not become ready')
subprocess.run([sys.executable,str(ROOT/'scripts/g2-persistence.py'),'verify','pod-recreation'],check=True)
save('g2/pod-recreation.json',{'start':start,'end':utc(),'commit':sha(),'old_pods':list(before),'new_pods':list(after),'old_uids':[p['metadata']['uid'] for p in before.values()],'new_uids':[p['metadata']['uid'] for p in after.values()],'result':'PASS'})
print('PASS: six replacement telemetry pods ready and historical markers preserved')
