#!/usr/bin/env python3
from labclient import *
import base64,urllib.parse,sys,uuid
marker=ROOT/'evidence/g2/persistence-marker.json'
def basic(base,path,body=None):
 req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Authorization':'Basic '+base64.b64encode(('lab:'+ENV['LAB_TOKEN']).encode()).decode()})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def promquery(base,t):return request(base,'/api/v1/query?query=up&time='+str(t),auth=False)[1]['data']['result']
def logs(base,id,start):
 q='{namespace="lab",app="worker"} |= "'+id+'"'
 return request(base,'/loki/api/v1/query_range?query='+urllib.parse.quote(q)+'&start='+str(int(start*1e9))+'&end='+str(int(time.time()*1e9))+'&limit=30',auth=False)[1]['data']['result']
mode=sys.argv[1]
if mode=='mark':
 assert not marker.exists(),'Existing marker must be preserved; do not overwrite evidence'
 start=time.time();run=uuid.uuid4().hex
 with forward('gateway',8080) as api:
  code,r,_=request(api,'/api/reports',{'subject':'synthetic-g2-persistence'},traffic='load',key='g2-persist-'+run);assert code==202
  result,_=wait_report(api,r['id'],traffic='load');assert result['state']=='completed'
 with forward('loki',3100) as loki:
  for _ in range(30):
   streams=logs(loki,r['id'],start-60)
   if streams:break
   time.sleep(2)
  assert streams,'Marker worker log missing'
 with forward('prometheus',9090) as prom:
  historical_time=time.time()-20;series=promquery(prom,historical_time);assert len(series)>=7 and all(x['value'][1]=='1' for x in series),series
 with forward('mailpit',8025) as inbox:
  messages=basic(inbox,'/api/v1/messages')['messages']
  initially_empty=not messages
  # Seed a clearly named delivery fixture if ephemeral G1 mailbox history
  # has already been lost. Never present the fixture as a live SLO alert.
  if not messages:
   import datetime
   now=datetime.datetime.now(datetime.timezone.utc)
   fixture=[{'labels':{'alertname':'G2PersistenceMarker','mode':'notification-fixture','severity':'info'},'annotations':{'summary':'Synthetic G2 persistence marker; not an SLO burn event'},'startsAt':(now-datetime.timedelta(seconds=5)).isoformat(),'endsAt':(now+datetime.timedelta(seconds=30)).isoformat()}]
   with forward('alertmanager',9093) as am:
    req=urllib.request.Request(am+'/api/v2/alerts',data=json.dumps(fixture).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:assert response.status==200
   for _ in range(30):
    messages=basic(inbox,'/api/v1/messages')['messages']
    if messages:break
    time.sleep(2)
  assert messages,'Local notification fixture was not delivered'
  mail_id=messages[0]['ID'];mail_subject=messages[0]['Subject']
 with forward('grafana',3000) as graf:
  annotation=basic(graf,'/api/annotations',{'time':int(start*1000),'tags':['g2-persistence'],'text':'synthetic-g2-marker-'+run});assert annotation['id']
 save('g2/persistence-marker.json',{'timestamp':utc(),'commit':sha(),'start_epoch':start,'historical_query_time':historical_time,'historical_up':series,'report_id':r['id'],'completed_result':result,'mail_id':mail_id,'mail_subject':mail_subject,'inbox_initially_empty':initially_empty,'grafana_annotation_id':annotation['id'],'log_lines':sum(len(x['values']) for x in streams),'purpose':'Markers recorded before telemetry migration; check same historical outcomes after pod/cluster recreation.'})
 print('PASS: historical metric/log/inbox/Grafana markers recorded')
elif mode=='verify':
 m=json.loads(marker.read_text())
 with forward('gateway',8080) as api:
  code,report,_=request(api,'/api/reports/'+m['report_id'],traffic='load');assert code==200 and report['state']=='completed' and report['result']==m['completed_result']['result'],report
 with forward('prometheus',9090) as prom:
  actual=promquery(prom,m['historical_query_time']);assert sorted(actual,key=lambda x:json.dumps(x['metric'],sort_keys=True))==sorted(m['historical_up'],key=lambda x:json.dumps(x['metric'],sort_keys=True)),(actual,m['historical_up'])
 with forward('loki',3100) as loki:
  streams=logs(loki,m['report_id'],m['start_epoch']-60);assert streams
  assert any('report.completed' in line[1] for stream in streams for line in stream['values']),streams
 with forward('mailpit',8025) as inbox:
  message=basic(inbox,'/api/v1/message/'+m['mail_id']);assert message['Subject']==m['mail_subject'],message
 with forward('grafana',3000) as graf:
  annotations=basic(graf,'/api/annotations?from='+str(int((m['start_epoch']-60)*1000))+'&to='+str(int(time.time()*1000))+'&tags=g2-persistence');assert any(a['id']==m['grafana_annotation_id'] for a in annotations),annotations
 pvcs=json.loads(kube('get','pvc','-o','json'))['items'];claims={p['metadata']['name']:p['status']['phase'] for p in pvcs}
 for name in ['prometheus','loki','grafana','alertmanager','mailpit','alloy']:assert claims.get(name+'-data')=='Bound',claims
 save('g2/persistence-'+sys.argv[2]+'.json',{'timestamp':utc(),'commit':sha(),'historical_up_preserved':True,'committed_report_result_preserved':True,'correlated_completed_log_preserved':True,'mail_message_preserved':m['mail_id'],'grafana_annotation_preserved':m['grafana_annotation_id'],'bound_claims':claims,'result':'PASS'})
 print('PASS: historical Prometheus/Loki/Mailpit/Grafana markers and six retained claims',sys.argv[2])
else:raise SystemExit('mark or verify STAGE required')
