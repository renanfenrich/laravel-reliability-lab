from pathlib import Path
import json
p=Path(__file__).resolve().parent.parent/'observability'
def w(n,data): (p/n).write_text(json.dumps(data,indent=2)+'\n')
rules=[]
def record(name,expr,labels=None):rules.append({'record':name,'expr':expr,**({'labels':labels} if labels else {})})
def alert(name,expr,severity,hold='2m',extra=None):rules.append({'alert':name,'expr':expr,'for':hold,'labels':{'severity':severity,'routing':'local-console',**(extra or {})},'annotations':{'summary':name,'runbook':'docs/runbooks/'+('telemetry.md' if name=='TelemetryUnavailable' else 'slow-processing.md' if 'Processing' in name else 'api-errors.md')}})
for window in ['5m','30m','1h','2h','6h','1d','3d','30d']:
    # API counter rates give request-weighted errors; normal traffic only.
    den=f'sum(rate(lab_http_total{{traffic="normal"}}[{window}]))'
    bad=f'sum(rate(lab_http_total{{traffic="normal",class="5xx"}}[{window}]))'
    total=f'sum(rate(lab_http_seconds_count{{traffic="normal"}}[{window}]))'
    fast=f'sum(rate(lab_http_seconds_bucket{{traffic="normal",le="0.5"}}[{window}]))'
    record('lab:api_availability_miss_ratio:'+window,f'{bad} / clamp_min({den}, 1e-12)')
    record('lab:api_latency_miss_ratio:'+window,f'clamp_min(({total} - {fast}) / clamp_min({total}, 1e-12), 0)')
    eligible=f'sum(lab_processing_cohort_total{{traffic="normal",window="{window}"}})'
    met=f'sum(lab_processing_cohort_met{{traffic="normal",window="{window}"}})'
    record('lab:processing_miss_ratio:'+window,f'({eligible} - {met}) / clamp_min({eligible}, 1)')
    for sli,budget in [('api_availability',.001),('api_latency',.01),('processing',.01)]:record('lab:'+sli+'_burn:'+window,f'lab:{sli}_miss_ratio:{window} / {budget}')
for sli in ['api_availability','api_latency','processing']:
    label={'sli':sli}
    for long,short,threshold,severity in [('1h','5m',14.4,'critical'),('6h','30m',6,'critical'),('1d','2h',3,'warning'),('3d','6h',1,'warning')]:
        alert('SLOBurn'+''.join(x.title() for x in sli.split('_'))+long,f'(lab:{sli}_burn:{long} > {threshold}) and (lab:{sli}_burn:{short} > {threshold}) and on() (up{{job="lab-exporter"}} == 1)',severity,extra=label)
record('lab:demo_processing_miss_ratio:5m','(sum(lab_processing_cohort_total{traffic="fault",window="5m"}) - sum(lab_processing_cohort_met{traffic="fault",window="5m"})) / clamp_min(sum(lab_processing_cohort_total{traffic="fault",window="5m"}),1)')
alert('LabDemoProcessingMiss','lab:demo_processing_miss_ratio:5m > 0','info','15s',{'mode':'accelerated-demonstration'})
alert('TelemetryUnavailable','(max(up{job="lab-exporter"}) == 0) or absent(max(up{job="lab-exporter"})) or absent(max(lab_telemetry_heartbeat_seconds)) or (max(time() - lab_scheduler_heartbeat_seconds) > 30)','warning','1m')
w('rules.yml',{'groups':[{'name':'lab-slo','interval':'15s','rules':rules}]})
w('prometheus.yml',{'global':{'scrape_interval':'5s','evaluation_interval':'15s'},'rule_files':['/etc/prometheus/rules.yml'],'scrape_configs':[{'job_name':'lab-exporter','metrics_path':'/api/metrics','static_configs':[{'targets':['exporter:8080']}]},{'job_name':'kube-state-metrics','static_configs':[{'targets':['kube-state-metrics:8080']}]},{'job_name':'prometheus','static_configs':[{'targets':['localhost:9090']}]},{'job_name':'kubelet-cadvisor','scheme':'https','metrics_path':'/metrics/cadvisor','kubernetes_sd_configs':[{'role':'node'}],'authorization':{'credentials_file':'/var/run/secrets/kubernetes.io/serviceaccount/token'},'tls_config':{'insecure_skip_verify':True},'relabel_configs':[{'source_labels':['__meta_kubernetes_node_name'],'target_label':'node'}]}]})
w('loki.yml',{'auth_enabled':False,'server':{'http_listen_port':3100},'common':{'path_prefix':'/loki','replication_factor':1,'ring':{'kvstore':{'store':'inmemory'}},'storage':{'filesystem':{'chunks_directory':'/loki/chunks','rules_directory':'/loki/rules'}}},'schema_config':{'configs':[{'from':'2024-01-01','store':'tsdb','object_store':'filesystem','schema':'v13','index':{'prefix':'index_','period':'24h'}}]},'limits_config':{'retention_period':'744h','allow_structured_metadata':True},'compactor':{'working_directory':'/loki/compactor','retention_enabled':True,'delete_request_store':'filesystem'},'analytics':{'reporting_enabled':False}})
(p/'config.alloy').write_text('discovery.kubernetes "lab" {\n  role = "pod"\n  namespaces {\n    names = ["lab"]\n  }\n}\ndiscovery.relabel "logs" {\n  targets = discovery.kubernetes.lab.targets\n  rule {\n    source_labels = ["__meta_kubernetes_namespace"]\n    target_label = "namespace"\n  }\n  rule {\n    source_labels = ["__meta_kubernetes_pod_label_app"]\n    target_label = "app"\n  }\n  rule {\n    source_labels = ["__meta_kubernetes_pod_container_name"]\n    target_label = "container"\n  }\n}\nloki.source.kubernetes "lab" {\n  targets = discovery.relabel.logs.output\n  forward_to = [loki.write.local.receiver]\n}\nloki.write "local" {\n  endpoint {\n    url = "http://loki:3100/loki/api/v1/push"\n  }\n}\n')
w('datasources.yml',{'apiVersion':1,'datasources':[{'name':'Prometheus','uid':'prometheus','type':'prometheus','access':'proxy','url':'http://prometheus:9090','isDefault':True},{'name':'Loki','uid':'loki','type':'loki','access':'proxy','url':'http://loki:3100'}]})
w('dashboards.yml',{'apiVersion':1,'providers':[{'name':'lab','type':'file','options':{'path':'/var/lib/grafana/dashboards'},'updateIntervalSeconds':10}]})
panels=[]
def panel(title,expr,unit='short',kind='timeseries',datasource='prometheus'):
    i=len(panels);panels.append({'id':i+1,'title':title,'type':kind,'datasource':{'uid':datasource,'type':datasource},'gridPos':{'x':(i%2)*12,'y':(i//2)*8,'w':12,'h':8},'targets':[{'refId':'A','expr':expr}], 'fieldConfig':{'defaults':{'unit':unit}},'options':{'legend':{'displayMode':'list'}}})
panel('API request rate by traffic and status class','sum by(traffic,class)(rate(lab_http_total[1m]))','reqps')
panel('API p99 latency — 500ms provisional threshold','histogram_quantile(0.99,sum by(le,traffic)(rate(lab_http_seconds_bucket[1m])))','s')
panel('Processing cohorts: misses include unfinished/failed at deadline','lab:processing_miss_ratio:5m','percentunit')
panel('30-day intended SLI window — incomplete history until 30d','lab:api_availability_miss_ratio:30d','percentunit')
panel('Reports by state and traffic','lab_reports')
panel('Overdue unfinished reports','lab_overdue_reports')
panel('Completion p99 (completed only; diagnostic, NOT processing SLI)','histogram_quantile(0.99,sum by(le,traffic)(rate(lab_processing_seconds_bucket[1m])))','s')
panel('Retries and lease recovery','sum by(traffic)(rate(lab_retries_total[1m]) + rate(lab_lease_recoveries_total[1m]))')
panel('External dependency latency','histogram_quantile(0.99,sum by(le,traffic)(rate(lab_external_seconds_bucket[1m])))','s')
panel('External dependency errors','sum by(traffic)(rate(lab_external_seconds_count{outcome="error"}[1m]))')
panel('Pod CPU — measured kubelet counters','sum by(pod)(rate(container_cpu_usage_seconds_total{namespace="lab",container!=""}[1m]))','cores')
panel('Pod working set memory','sum by(pod)(container_memory_working_set_bytes{namespace="lab",container!=""})','bytes')
panel('Pod restarts','kube_pod_container_status_restarts_total{namespace="lab"}')
panel('Active alerts and routing severity','ALERTS{alertstate="firing"}')
panel('Structured report logs: filter request_id/report_id in Explore','{namespace="lab",app=~"api|worker|scheduler"} | json','short','logs','loki')
w('dashboard.json',{'uid':'reliability-lab','title':'Laravel local reliability lab','schemaVersion':39,'version':1,'tags':['local-lab','provisional-slo'],'refresh':'5s','time':{'from':'now-15m','to':'now'},'panels':panels,'annotations':{'list':[]}})
