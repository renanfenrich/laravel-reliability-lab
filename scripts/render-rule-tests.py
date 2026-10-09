from pathlib import Path
import json
p=Path('observability')
series_windows=['5m','30m','1h','2h','6h','1d','3d','30d']
def fixture(good=1000,bad=0,fast=1000,total=1000,met=10000,cohort=10000,length=43201):
    s=[]
    def add(name,values):s.append({'series':name,'values':values})
    add('up{job="lab-exporter"}',f'1+0x{length}')
    for name in ['lab_scheduler_heartbeat_seconds','lab_telemetry_heartbeat_seconds']:add(name,f'0+60x{length}')
    add('lab_http_total{traffic="normal",route="submit",class="2xx"}',f'0+{good}x{length}')
    add('lab_http_total{traffic="normal",route="submit",class="5xx"}',f'0+{bad}x{length}')
    add('lab_http_seconds_count{traffic="normal",route="submit",class="2xx"}',f'0+{total}x{length}')
    add('lab_http_seconds_bucket{traffic="normal",route="submit",class="2xx",le="0.5"}',f'0+{fast}x{length}')
    for window in series_windows:
        add(f'lab_processing_cohort_total{{traffic="normal",window="{window}"}}',f'{cohort}+0x{length}')
        add(f'lab_processing_cohort_met{{traffic="normal",window="{window}"}}',f'{met}+0x{length}')
    for name in ['lab_processing_cohort_total','lab_processing_cohort_met']:add(name+'{traffic="fault",window="5m"}',f'0+0x{length}')
    return s

def expectation(name,severity='critical',sli=None,mode=None):
    labels={'severity':severity,'routing':'local-console'}
    if sli:labels['sli']=sli
    if mode:labels['mode']=mode
    return {'exp_labels':labels,'exp_annotations':{'summary':name,'runbook':'docs/runbooks/'+('telemetry.md' if name=='TelemetryUnavailable' else 'slow-processing.md' if 'Processing' in name else 'api-errors.md')}}
tests=[]
def test(name,s,checks=None,exprs=None):
    tests.append({'name':name,'interval':'1m','input_series':s,'alert_rule_test':checks or [],'promql_expr_test':exprs or []})
def expr(name,value,when='90m'):
    return {'expr':'round('+name+', 1e-9)','eval_time':when,'exp_samples':[{'labels':'{}','value':value}]}
allnames=['SLOBurn'+''.join(x.title() for x in sli.split('_'))+window for sli in ['api_availability','api_latency','processing'] for window in ['1h','6h','1d','3d']]+['TelemetryUnavailable','LabDemoProcessingMiss']
test('healthy traffic',fixture(length=120),[{'eval_time':'90m','alertname':n,'exp_alerts':[]} for n in allnames],[expr('lab:api_availability_miss_ratio:30d',0),expr('lab:processing_miss_ratio:30d',0)])
n='SLOBurnApiAvailability1h';test('5% eligible server failures burn availability budget',fixture(good=950,bad=50,length=120),[{'eval_time':'90m','alertname':n,'exp_alerts':[expectation(n,sli='api_availability')]}],[expr('lab:api_availability_burn:1h',50,'90m')])
n='SLOBurnApiLatency1h';test('20% over 500ms burns latency budget',fixture(fast=800,length=120),[{'eval_time':'90m','alertname':n,'exp_alerts':[expectation(n,sli='api_latency')]}],[expr('lab:api_latency_miss_ratio:1h',.2,'90m')])
n='SLOBurnProcessing1h';test('failed and unfinished expired reports are misses',fixture(met=8000,length=120),[{'eval_time':'90m','alertname':n,'exp_alerts':[expectation(n,sli='processing')]}],[expr('lab:processing_miss_ratio:1h',.2,'90m')])
s=fixture(good=0,total=0,fast=0,met=0,cohort=0,length=120);test('zero traffic is no evidence and does not page',s,[{'eval_time':'90m','alertname':n,'exp_alerts':[]} for n in allnames],[expr('lab:api_availability_miss_ratio:1h',0,'90m'),expr('lab:processing_miss_ratio:1h',0,'90m')])
s=fixture(length=120);s[0]['values']='0+0x120';n='TelemetryUnavailable';test('scrape target fails independently of SLO claims',s,[{'eval_time':'5m','alertname':n,'exp_alerts':[expectation(n,'warning')]}])
test('all telemetry absent is unknown',[],[{'eval_time':'5m','alertname':'TelemetryUnavailable','exp_alerts':[expectation('TelemetryUnavailable','warning')]}])
s=fixture(length=240)
for row in s:
 if row['series'].startswith('lab_http_total'):
  row['values']='0+950x120 114950+1000x119' if '2xx' in row['series'] else '0+50x120 6000+0x119'
n='SLOBurnApiAvailability1h';test('healthy recovery resolves fast availability burn',s,[{'eval_time':'4h','alertname':n,'exp_alerts':[]}],[expr('lab:api_availability_burn:1h',0,'4h')])
s=fixture(length=120)
for row in s:
 if row['series'].startswith('lab_processing_cohort_total{traffic="fault"'):row['values']='10+0x120'
 if row['series'].startswith('lab_processing_cohort_met{traffic="fault"'):row['values']='5+0x120'
n='LabDemoProcessingMiss';test('accelerated fault demonstration is separate',s,[{'eval_time':'5m','alertname':n,'exp_alerts':[expectation(n,'info',mode='accelerated-demonstration')]}],[expr('lab:processing_miss_ratio:1h',0,'5m')])
(p/'tests.yml').write_text(json.dumps({'rule_files':['rules.yml'],'evaluation_interval':'15s','fuzzy_compare':True,'tests':tests},indent=2)+'\n')

source=json.loads((p/'rules.yml').read_text())['groups'][0]['rules']
selected=[r for r in source if r.get('record','').endswith((':6h',':3d',':30d')) or r.get('alert','').endswith('3d')]
(p/'rules-long.yml').write_text(json.dumps({'groups':[{'name':'same-intended-long-window-expressions','interval':'1h','rules':selected}]},indent=2)+'\n')
longtests=[]
for name,kwargs,availability,latency,processing in [('healthy 30d',{},0,0,0),('violations 30d',{'good':950,'bad':50,'fast':800,'met':8000},.05,.2,.2),('zero volume 30d',{'good':0,'bad':0,'total':0,'fast':0,'met':0,'cohort':0},0,0,0)]:
    longtests.append({'name':name,'interval':'1h','input_series':fixture(length=721,**kwargs),'promql_expr_test':[expr('lab:api_availability_miss_ratio:30d',availability,'30d'),expr('lab:api_latency_miss_ratio:30d',latency,'30d'),expr('lab:processing_miss_ratio:30d',processing,'30d')], 'alert_rule_test':[{'eval_time':'30d','alertname':'SLOBurnApiAvailability3d','exp_alerts':[expectation('SLOBurnApiAvailability3d','warning','api_availability')] if availability else []}]})
(p/'tests-long.yml').write_text(json.dumps({'rule_files':['rules-long.yml'],'evaluation_interval':'1h','fuzzy_compare':True,'tests':longtests},indent=2)+'\n')
