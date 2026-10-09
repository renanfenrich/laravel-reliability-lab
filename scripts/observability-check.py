from labclient import *
import urllib.parse
start=utc()
with forward('prometheus',9090) as base:
    _,targets,_=request(base,'/api/v1/targets',auth=False)
    active=targets['data']['activeTargets']; assert len(active)>=4 and all(t['health']=='up' for t in active),[(t['labels'],t['health'],t.get('lastError')) for t in active]
    checks={}
    for expr in ['lab_accepted_total','lab_completed_total','lab_processing_cohort_total','container_memory_working_set_bytes{namespace="lab"}','kube_pod_container_status_restarts_total{namespace="lab"}']:
        _,r,_=request(base,'/api/v1/query?query='+urllib.parse.quote(expr),auth=False);assert r['data']['result'],expr;checks[expr]=len(r['data']['result'])
with forward('loki',3100) as base:
    report_id=json.loads((ROOT/'evidence/smoke.json').read_text())['unique_report']
    q='{namespace="lab",app="worker"} | json report_id="context.report_id", request_id="context.request_id" | report_id="'+report_id+'"'
    for _ in range(30):
        _,r,_=request(base,'/loki/api/v1/query_range?query='+urllib.parse.quote(q)+'&limit=10',auth=False)
        streams=r['data']['result']
        if streams:break
        time.sleep(2)
    assert streams,'Worker logs absent in Loki'
    text=' '.join(v[1] for stream in streams for v in stream['values']);assert 'report_id' in text and 'request_id' in text,text[:200]
with forward('grafana',3000) as base:
    req=urllib.request.Request(base+'/api/dashboards/uid/reliability-lab')
    import base64
    req.add_header('Authorization','Basic '+base64.b64encode(('lab:'+ENV['LAB_TOKEN']).encode()).decode())
    with urllib.request.urlopen(req,timeout=10) as r: dashboard=json.loads(r.read())
    assert len(dashboard['dashboard']['panels'])>=14
    def grafana(path,body=None):
        req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None)
        req.add_header('Authorization','Basic '+base64.b64encode(('lab:'+ENV['LAB_TOKEN']).encode()).decode())
        req.add_header('Content-Type','application/json')
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())
    datasource_health={uid:grafana('/api/datasources/uid/'+uid+'/health') for uid in ['prometheus','loki']}
    assert all(r.get('status')=='OK' for r in datasource_health.values()),datasource_health
    panel_checks={}
    for panel in dashboard['dashboard']['panels']:
        target=panel['targets'][0]
        query={**target,'datasource':panel['datasource'],'intervalMs':15000,'maxDataPoints':240,'range':True}
        result=grafana('/api/ds/query',{'from':str(int((time.time()-3600)*1000)),'to':str(int(time.time()*1000)),'queries':[query]})['results'][target['refId']]
        assert not result.get('error') and result.get('status',200)==200,(panel['title'],result)
        panel_checks[panel['title']]=len(result.get('frames',[]))
    assert panel_checks['Reports by state and traffic']>0,panel_checks
    assert panel_checks['Pod working set memory']>0,panel_checks
    assert panel_checks['Structured report logs: filter request_id/report_id in Explore']>0,panel_checks
save('observability.json',{'start':start,'end':utc(),'commit':sha(),'targets':[{'job':t['labels'].get('job'),'health':t['health']} for t in active],'metric_series':checks,'searchable_correlated_worker_logs':True,'queried_report_id':report_id,'dashboard_panels':len(dashboard['dashboard']['panels']),'grafana_datasource_health':datasource_health,'grafana_panel_frames':panel_checks,'result':'PASS'})
print('PASS: Prometheus targets/resource metrics, Loki correlated worker logs and provisioned Grafana dashboard')
