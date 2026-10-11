#!/usr/bin/env python3
from labclient import *
from collections import Counter
import concurrent.futures, uuid
start=utc();serving=Counter()
with forward('gateway',8080) as base:
 def get(_):
  with urllib.request.urlopen(base+'/api/live',timeout=10) as r:
   assert r.status==200
   assert json.load(r)['status']=='alive'
   return r.headers['X-Lab-API-Pod']
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:serving.update(pool.map(get,range(80)))
 ready_pods={p['metadata']['name'] for p in json.loads(kube('get','pods','-l','app=api','-o','json'))['items'] if all(c['ready'] for c in p['status']['containerStatuses'])}
 assert len(ready_pods)==2 and set(serving)==ready_pods,(serving,ready_pods)
 key='g2-runtime-'+uuid.uuid4().hex
 code,r,_=request(base,'/api/reports',{'subject':'synthetic-g2-runtime'},traffic='load',key=key);assert code==202,r
 result,_=wait_report(base,r['id'],traffic='load');assert result['state']=='completed' and result['result']['checksum'],result
 assert request(base,'/api/reports',{'subject':'synthetic-g2-runtime'},traffic='load',key=key)[0]==200
 assert request(base,'/api/reports',{'subject':'synthetic-g2-runtime'},traffic='load',key=key,auth=False)[0]==401
row=kube('exec','deployment/postgres','--','psql','-U','lab','-d','lab','-Atc',f"SELECT state,attempts,result->>'checksum' FROM reports WHERE id='{r['id']}'").strip();assert row.startswith('completed|1|'),row
save('g2/runtime.json',{'start':start,'end':utc(),'commit':sha(),'gateway':'gateway -> API ClusterIP -> two NGINX/FPM pods','serving_pods':dict(serving),'report_id':r['id'],'database_result':row,'result':'PASS'})
print('PASS: NGINX/FPM gateway reached both API replicas, authenticated durable journey and idempotent replay',dict(serving))
