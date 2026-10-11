#!/usr/bin/env python3
from labclient import *
import base64,datetime,uuid,urllib.parse,sys
run='email-'+uuid.uuid4().hex[:10]
folder=ROOT/'evidence'/run;folder.mkdir()
def record(name,data):(folder/name).write_text(json.dumps(data,indent=2)+'\n')
def mail(base,path):
 req=urllib.request.Request(base+path,headers={'Authorization':'Basic '+base64.b64encode(('lab:'+ENV['LAB_TOKEN']).encode()).decode()})
 with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
def post(base,payload):
 req=urllib.request.Request(base+'/api/v2/alerts',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=10) as r:assert r.status==200

def wait(condition,label,seconds):
 end=time.monotonic()+seconds;last=0
 while time.monotonic()<end:
  result=condition()
  if result:return result
  if time.monotonic()-last>40:print(utc(),'WAIT',label,flush=True);last=time.monotonic()
  time.sleep(3)
 raise TimeoutError(label)
def timestamp(delta=0):return (datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=delta)).isoformat()
print('EVIDENCE',folder.relative_to(ROOT),flush=True)
record('context.json',{'start':utc(),'commit':sha(),'run':run,'note':'SLO rule unit tests separate from notification-fixture injection. Live fault/telemetry experiments below.'})
with forward('mailpit',8025) as inbox,forward('alertmanager',9093) as am,forward('prometheus',9090) as prom,forward('api',8080) as api:
 baseline={m['ID'] for m in mail(inbox,'/api/v1/messages')['messages']}
 rules=[r for g in json.loads((ROOT/'observability/rules.yml').read_text())['groups'] for r in g['rules'] if 'alert' in r]
 started=timestamp(-10)
 injected=[{'labels':{**r['labels'],'alertname':r['alert'],'mode':'notification-fixture-'+run},'annotations':{**r['annotations'],'summary':'NOTIFICATION FIXTURE: '+r['alert']},'startsAt':started,'endsAt':timestamp(180)} for r in rules]
 post(am,injected)
 names={r['alert'] for r in rules}
 def subjects():return [m['Subject'] for m in mail(inbox,'/api/v1/messages')['messages'] if m['ID'] not in baseline]
 wait(lambda:all(any('[FIRING]' in s and name+' ' in s and run in s for s in subjects()) for name in names),'all fixture firing emails',90)
 print('PASS: firing email for all',len(names),'alert routes',flush=True)
 for a in injected:a['endsAt']=timestamp(-1)
 post(am,injected)
 wait(lambda:all(any('[RESOLVED]' in s and name+' ' in s and run in s for s in subjects()) for name in names),'all fixture resolved emails',90)
 print('PASS: resolved email for all notification fixtures',flush=True)
 record('notification-fixtures.json',{'run':run,'alerts':sorted(names),'firing_and_resolved_received':True,'subjects':subjects(),'source':'Alertmanager API injection, NOT live SLO burn evidence'})
 code,r,_=request(api,'/api/reports',{'subject':'synthetic-email-alert','latency_ms':100,'fail_attempts':3},traffic='fault',key=run)
 assert code==202,r
 failed,_=wait_report(api,r['id'],90,traffic='fault');assert failed['state']=='failed',failed
 record('failed-report.json',{'id':r['id'],'result':failed,'timestamp':utc(),'traffic':'fault'})
 original=json.loads(kube('get','deployment/scheduler','-o','json'))['spec']['replicas'];assert original==1
 live_names=['LabDemoProcessingMiss','TelemetryUnavailable','InfrastructureTelemetryUnavailable'];events=[]
 def snapshot():
  _,data,_=request(prom,'/api/v1/alerts',auth=False)
  events.append({'timestamp':utc(),'alerts':data['data']['alerts']})
  return data['data']['alerts']
 try:
  kube('scale','deployment/scheduler','--replicas=0')
  subprocess.run([sys.executable,str(ROOT/'scripts/host-metrics-control.py'),'stop'],check=True)
  print(utc(),'LIVE FAULT: scheduler paused, host collector stopped',flush=True)
  wait(lambda:all(any(a['labels'].get('alertname')==n and a['state']=='firing' for a in snapshot()) for n in live_names),'three real Prometheus alerts firing',200)
  wait(lambda:all(any('[FIRING]' in s and n in s and 'notification-fixture' not in s for s in subjects()) for n in live_names),'three real firing emails',60)
  print('PASS: real fault + telemetry alerts fired and delivered',flush=True)
 finally:
  kube('scale','deployment/scheduler','--replicas='+str(original))
  subprocess.run([sys.executable,str(ROOT/'scripts/host-metrics-control.py'),'start'],check=True)
  kube('rollout','status','deployment/scheduler','--timeout=120s')
  print(utc(),'RESTORED: scheduler and host collector',flush=True)
 wait(lambda:not any(a['labels'].get('alertname') in live_names for a in snapshot()),'real alert recovery / fault cohort aging',400)
 wait(lambda:all(any('[RESOLVED]' in s and n in s and 'notification-fixture' not in s for s in subjects()) for n in live_names),'three real resolved emails',60)
 messages=mail(inbox,'/api/v1/messages')['messages'];captured=[]
 for message in messages:
  if message['ID'] in baseline:continue
  captured.append(mail(inbox,'/api/v1/message/'+message['ID']))
 record('mail-messages.json',captured)
 record('live-alerts.json',{'events':events,'report_id':r['id'],'firing_and_resolved_email_received':live_names,'end':utc(),'result':'PASS'})
print('PASS: rule-route fixtures and three real firing/resolved deliveries',flush=True)
