#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,copy
root=Path(__file__).resolve().parent.parent
objects={}
def source_hash(dirs,files):
    paths=[root/f for f in files]
    for d in dirs:paths.extend((root/d).rglob('*.php'))
    data=b''.join(str(f.relative_to(root)).encode()+b'\0'+f.read_bytes() for f in sorted(paths) if f.is_file() and 'cache' not in f.parts)
    return hashlib.sha256(data).hexdigest()
apphash=source_hash(['app','bootstrap','config','database','routes','public'],['Dockerfile','.dockerignore','composer.json','composer.lock','artisan','runtime/php-fpm.conf'])
simhash=source_hash([],['simulator/Dockerfile','simulator/server.py'])
def add(o):
    key=o['kind'].lower()+'-'+o['metadata']['name']; objects[key]=o
    return o

def obj(kind,name,spec=None,api='v1',**extra):
    o={'apiVersion':api,'kind':kind,'metadata':{'name':name,'namespace':'lab'},**extra}
    if spec is not None:o['spec']=spec
    return add(o)
def secret(name,key=None):return {'name':name,'valueFrom':{'secretKeyRef':{'name':'lab-secrets','key':key or name}}}
def service(name,port):obj('Service',name,{'selector':{'app':name},'ports':[{'port':port,'targetPort':port,'name':'http' if port not in [5432,6379] else 'tcp'}]})
def deploy(name,image,port,command=None,args=None,env=None,volumes=None,mounts=None,replicas=1,requests=None,limits=None,probe=None,user=1000,sa=None,init=None):
    c={'name':name,'image':image,'imagePullPolicy':'IfNotPresent','ports':[{'containerPort':port,'name':'http'}], 'resources':{'requests':requests or {'cpu':'100m','memory':'128Mi'},'limits':limits or {'cpu':'1','memory':'384Mi'}},'securityContext':{'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']},'readOnlyRootFilesystem':user!=None}}
    if user is None:c['securityContext']['capabilities']['add']=['CHOWN','SETUID','SETGID','DAC_OVERRIDE','FOWNER']
    if user is not None:c['securityContext'].update({'runAsUser':user,'runAsNonRoot':True})
    if command:c['command']=command
    if args:c['args']=args
    if env:c['env']=env
    if mounts:c['volumeMounts']=mounts
    if probe:
        c['startupProbe']={**probe,'failureThreshold':60,'periodSeconds':3,'timeoutSeconds':2}
        c['readinessProbe']={**probe,'periodSeconds':5,'timeoutSeconds':3}
        c['livenessProbe']={**probe,'periodSeconds':10,'timeoutSeconds':3,'failureThreshold':6}
    pod={'containers':[c],'terminationGracePeriodSeconds':25,'automountServiceAccountToken':bool(sa),'securityContext':{'seccompProfile':{'type':'RuntimeDefault'}},'volumes':copy.deepcopy(volumes or [])}
    if not volumes:pod.pop('volumes')
    if user is not None:pod['securityContext']['fsGroup']=user
    if sa:pod['serviceAccountName']=sa
    if init:pod['initContainers']=init
    obj('Deployment',name,{'replicas':replicas,'strategy':{'type':'Recreate'} if name in ['postgres','redis'] else {'type':'RollingUpdate'},'selector':{'matchLabels':{'app':name}},'template':{'metadata':{'labels':{'app':name}},'spec':pod}},api='apps/v1')
    service(name,port)
def config(name,data):obj('ConfigMap',name,data=data)
def configvol(name,path):return ({'name':name,'configMap':{'name':name}},{'name':name,'mountPath':path,'readOnly':True})
def role(name,rules,cluster=False):
    obj('ServiceAccount',name)
    kind='ClusterRole' if cluster else 'Role'
    o=obj(kind,name,api='rbac.authorization.k8s.io/v1',rules=rules)
    if cluster:o['metadata'].pop('namespace',None);o['metadata']['name']='laravel-reliability-'+name
    b=obj('ClusterRoleBinding' if cluster else 'RoleBinding',name,api='rbac.authorization.k8s.io/v1',roleRef={'apiGroup':'rbac.authorization.k8s.io','kind':kind,'name':o['metadata']['name']},subjects=[{'kind':'ServiceAccount','name':name,'namespace':'lab'}])
    if cluster:b['metadata'].pop('namespace',None);b['metadata']['name']='laravel-reliability-'+name

pv=obj('PersistentVolume','laravel-reliability-postgres',{'capacity':{'storage':'5Gi'},'accessModes':['ReadWriteOnce'],'persistentVolumeReclaimPolicy':'Retain','storageClassName':'lab-static','hostPath':{'path':'/lab-postgres','type':'DirectoryOrCreate'},'claimRef':{'namespace':'lab','name':'postgres-data'}});pv['metadata'].pop('namespace')
obj('PersistentVolumeClaim','postgres-data',{'accessModes':['ReadWriteOnce'],'storageClassName':'lab-static','volumeName':'laravel-reliability-postgres','resources':{'requests':{'storage':'5Gi'}}})
pgprobe={'exec':{'command':['pg_isready','-U','lab','-d','lab']}}
deploy('postgres','postgres:18.0-bookworm',5432,env=[{'name':'POSTGRES_DB','value':'lab'},{'name':'POSTGRES_USER','value':'lab'},secret('POSTGRES_PASSWORD')],volumes=[{'name':'data','persistentVolumeClaim':{'claimName':'postgres-data'}}],mounts=[{'name':'data','mountPath':'/var/lib/postgresql'}],probe=pgprobe,user=None,limits={'cpu':'2','memory':'512Mi'})
deploy('redis','redis:8.2.2-bookworm',6379,command=['sh','-c','exec redis-server --appendonly yes --requirepass "$REDIS_PASSWORD"'],env=[secret('REDIS_PASSWORD')],volumes=[{'name':'data','emptyDir':{}}],mounts=[{'name':'data','mountPath':'/data'}],probe={'exec':{'command':['sh','-c','REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping | grep -q PONG']}},user=None,limits={'cpu':'1','memory':'256Mi'})
deploy('simulator','laravel-reliability-simulator:g2',8081,probe={'httpGet':{'path':'/live','port':8081}},limits={'cpu':'1','memory':'128Mi'})
appenv=[secret(n) for n in ['APP_KEY','DB_PASSWORD','REDIS_PASSWORD','LAB_TOKEN']]+[{'name':'APP_ENV','value':'local'},{'name':'LAB_FAULTS','value':'true'},{'name':'DB_HOST','value':'postgres'},{'name':'REDIS_HOST','value':'redis'},{'name':'SIMULATOR_URL','value':'http://simulator:8081'}]
vols=[{'name':n,'emptyDir':{}} for n in ['storage','cache','tmp']]
mounts=[{'name':'storage','mountPath':'/app/storage'},{'name':'cache','mountPath':'/app/bootstrap/cache'},{'name':'tmp','mountPath':'/tmp'}]
# Mounting empty storage requires framework directories before application boot.
init=[{'name':'storage-init','image':'laravel-reliability-app:g2','imagePullPolicy':'IfNotPresent','resources':{'requests':{'cpu':'25m','memory':'16Mi'},'limits':{'cpu':'100m','memory':'64Mi'}},'command':['sh','-c','mkdir -p /app/storage/framework/cache /app/storage/framework/views /app/storage/framework/sessions /app/storage/logs'],'volumeMounts':mounts,'securityContext':{'runAsUser':1000,'runAsNonRoot':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}}]
for name in ['api','worker','scheduler','exporter']:
    cmd=['php-fpm','--nodaemonize'] if name in ['api','exporter'] else ['php','artisan']+(['queue:work','redis','--queue=reports','--sleep=1','--timeout=10','--tries=1'] if name=='worker' else ['schedule:work'])
    env=appenv+[{'name':'LAB_ROLE','value':name}]
    probe={'httpGet':{'path':'/api/ready','port':8080}} if name in ['api','exporter'] else {'exec':{'command':['php','artisan','lab:ready']}}
    deploy(name,'laravel-reliability-app:g2',8080,command=cmd,env=env,volumes=vols,mounts=mounts,replicas=2 if name in ['api','worker'] else 1,probe=probe,init=init)
    c=objects['deployment-'+name]['spec']['template']['spec']['containers'][0]
    c['livenessProbe']={'httpGet':{'path':'/api/live','port':8080},'periodSeconds':10,'failureThreshold':3} if name in ['api','exporter'] else {'exec':{'command':['php','-r',"exit(str_contains(file_get_contents('/proc/1/cmdline'), 'artisan') ? 0 : 1);"]},'periodSeconds':10,'failureThreshold':3}

# NGINX sidecars expose HTTP; FPM/status ports stay internal to each pod.
config('nginx-api',{'nginx.conf':(root/'runtime/nginx-api.conf').read_text()})
for name in ['api','exporter']:
    pod=objects['deployment-'+name]['spec']['template']['spec']
    pod['containers'][0]['ports']=[{'containerPort':9000,'name':'fastcgi'}]
    pod['containers'][0]['lifecycle']={'preStop':{'exec':{'command':['sh','-c','sleep 3; kill -QUIT 1']}}}
    v,m=configvol('nginx-api','/etc/lab-nginx');pod['volumes'].append(v)
    sidecar={'name':'http','image':'nginx:1.30.5-alpine','imagePullPolicy':'IfNotPresent','command':['nginx','-c','/etc/lab-nginx/nginx.conf','-g','daemon off;'],'ports':[{'containerPort':8080,'name':'http'}],'resources':{'requests':{'cpu':'50m','memory':'32Mi'},'limits':{'cpu':'500m','memory':'128Mi'}},'securityContext':{'runAsUser':1000,'runAsNonRoot':True,'allowPrivilegeEscalation':False,'readOnlyRootFilesystem':True,'capabilities':{'drop':['ALL']}},'volumeMounts':[m,{'name':'tmp','mountPath':'/tmp'}],'lifecycle':{'preStop':{'exec':{'command':['sh','-c','sleep 3; nginx -c /etc/lab-nginx/nginx.conf -s quit']}}}}
    fpm=pod['containers'][0]
    fpm['startupProbe']={'httpGet':{'path':'/fpm-live','port':8082},'periodSeconds':3,'timeoutSeconds':2,'failureThreshold':60}
    fpm['livenessProbe']={'httpGet':{'path':'/fpm-live','port':8082},'periodSeconds':10,'timeoutSeconds':2,'failureThreshold':3}
    for probe in ['startupProbe','readinessProbe','livenessProbe']:
        sidecar[probe]={'httpGet':{'path':'/http-live','port':8082},'periodSeconds':5 if probe=='readinessProbe' else 10,'timeoutSeconds':2,'failureThreshold':3}
    sidecar['startupProbe'].update({'periodSeconds':3,'failureThreshold':60})
    pod['containers'].append(sidecar)
obj('Service','api-diagnostics',{'clusterIP':'None','publishNotReadyAddresses':True,'selector':{'app':'api'},'ports':[{'port':8082,'targetPort':8082,'name':'diagnostics'}]})
config('nginx-gateway',{'nginx.conf':(root/'runtime/nginx-gateway.conf').read_text()})
v,m=configvol('nginx-gateway','/etc/lab-nginx')
deploy('gateway','nginx:1.30.5-alpine',8080,command=['nginx','-c','/etc/lab-nginx/nginx.conf','-g','daemon off;'],volumes=[v,{'name':'tmp','emptyDir':{}}],mounts=[m,{'name':'tmp','mountPath':'/tmp'}],probe={'httpGet':{'path':'/api/ready','port':8080}},limits={'cpu':'1','memory':'128Mi'})
objects['deployment-gateway']['spec']['template']['spec']['containers'][0]['livenessProbe']={'httpGet':{'path':'/gateway/live','port':8080},'periodSeconds':10,'failureThreshold':3}

if (root/'observability/prometheus.yml').exists():
    config('prometheus',{'prometheus.yml':(root/'observability/prometheus.yml').read_text(),'rules.yml':(root/'observability/rules.yml').read_text()})
    v,m=configvol('prometheus','/etc/prometheus'); deploy('prometheus','prom/prometheus:v3.15.0',9090,args=['--config.file=/etc/prometheus/prometheus.yml','--storage.tsdb.path=/prometheus','--storage.tsdb.retention.time=31d'],volumes=[v,{'name':'data','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/prometheus'}],user=65534,probe={'httpGet':{'path':'/-/ready','port':9090}},limits={'cpu':'2','memory':'768Mi'},sa='prometheus')
    host_address=(root/'.runtime/host-metrics-address').read_text().strip() if (root/'.runtime/host-metrics-address').exists() else '172.19.0.1'
    objects['deployment-prometheus']['spec']['template']['spec']['hostAliases']=[{'ip':host_address,'hostnames':['lab-host-metrics']}]
    role('prometheus',[{'apiGroups':[''],'resources':['nodes'],'verbs':['get','list','watch']},{'apiGroups':[''],'resources':['nodes/metrics'],'verbs':['get']}],True)
    config('alertmanager',{'alertmanager.yml':(root/'observability/alertmanager.yml').read_text()})
    v,m=configvol('alertmanager','/etc/alertmanager')
    deploy('alertmanager','prom/alertmanager:v0.34.1',9093,args=['--config.file=/etc/alertmanager/alertmanager.yml','--storage.path=/alertmanager','--cluster.listen-address='],volumes=[v,{'name':'data','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/alertmanager'}],user=65534,probe={'httpGet':{'path':'/-/ready','port':9093}},limits={'cpu':'500m','memory':'128Mi'})
    deploy('mailpit','axllent/mailpit:v1.31.5',8025,env=[{'name':'MP_DATABASE','value':'/data/mailpit.db'},{'name':'MP_UI_AUTH_FILE','value':'/auth/MAILPIT_UI_AUTH'},{'name':'MP_ENABLE_PROMETHEUS','value':'0.0.0.0:9090'},{'name':'MP_SMTP_ALLOWED_RECIPIENTS','value':'^alerts@lab[.]test$'},{'name':'MP_SMTP_DISABLE_RDNS','value':'true'},{'name':'MP_BLOCK_REMOTE_CSS_AND_FONTS','value':'true'}],volumes=[{'name':'data','emptyDir':{}},{'name':'auth','secret':{'secretName':'lab-secrets','items':[{'key':'MAILPIT_UI_AUTH','path':'MAILPIT_UI_AUTH'}]}}],mounts=[{'name':'data','mountPath':'/data'},{'name':'auth','mountPath':'/auth','readOnly':True}],user=1000,probe={'tcpSocket':{'port':8025}},limits={'cpu':'500m','memory':'128Mi'})
    objects['deployment-mailpit']['spec']['template']['spec']['containers'][0]['ports'] += [{'containerPort':1025,'name':'smtp'},{'containerPort':9090,'name':'metrics'}]
    objects['service-mailpit']['spec']['ports'] += [{'port':1025,'targetPort':1025,'name':'smtp'},{'port':9090,'targetPort':9090,'name':'metrics'}]
    config('loki',{'loki.yml':(root/'observability/loki.yml').read_text()})
    v,m=configvol('loki','/etc/loki');deploy('loki','grafana/loki:3.7.8',3100,args=['-config.file=/etc/loki/loki.yml'],volumes=[v,{'name':'data','emptyDir':{}},{'name':'tmp','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/loki'},{'name':'tmp','mountPath':'/tmp'}],user=10001,probe={'httpGet':{'path':'/ready','port':3100}},limits={'cpu':'1','memory':'512Mi'})
    config('alloy',{'config.alloy':(root/'observability/config.alloy').read_text()})
    v,m=configvol('alloy','/etc/alloy');deploy('alloy','grafana/alloy:v1.20.1',12345,args=['run','/etc/alloy/config.alloy','--server.http.listen-addr=0.0.0.0:12345','--storage.path=/alloy'],volumes=[v,{'name':'data','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/alloy'}],user=1000,probe={'httpGet':{'path':'/-/ready','port':12345}},sa='alloy',limits={'cpu':'1','memory':'256Mi'})
    role('alloy',[{'apiGroups':[''],'resources':['pods'],'verbs':['get','list','watch']},{'apiGroups':[''],'resources':['pods/log'],'verbs':['get']}])
    config('grafana-datasources',{'datasources.yml':(root/'observability/datasources.yml').read_text()})
    config('grafana-provider',{'dashboards.yml':(root/'observability/dashboards.yml').read_text()})
    config('grafana-dashboard',{'lab.json':(root/'observability/dashboard.json').read_text(),'infrastructure.json':(root/'observability/infrastructure-dashboard.json').read_text()})
    pairs=[configvol(n,path) for n,path in [('grafana-datasources','/etc/grafana/provisioning/datasources'),('grafana-provider','/etc/grafana/provisioning/dashboards'),('grafana-dashboard','/var/lib/grafana/dashboards')]]
    deploy('grafana','grafana/grafana:13.2.3',3000,env=[secret('GF_SECURITY_ADMIN_USER'),secret('GF_SECURITY_ADMIN_PASSWORD'),{'name':'GF_PLUGINS_PREINSTALL_DISABLED','value':'true'},{'name':'GF_PLUGINS_PREINSTALL_AUTO_UPDATE','value':'false'},{'name':'GF_ANALYTICS_REPORTING_ENABLED','value':'false'},{'name':'GF_ANALYTICS_CHECK_FOR_UPDATES','value':'false'}],volumes=[x[0] for x in pairs]+[{'name':'data','emptyDir':{}},{'name':'tmp','emptyDir':{}}],mounts=[x[1] for x in pairs]+[{'name':'data','mountPath':'/var/lib/grafana'},{'name':'tmp','mountPath':'/tmp'}],user=472,probe={'httpGet':{'path':'/api/health','port':3000}},limits={'cpu':'1','memory':'1Gi'})
    role('kube-state-metrics',[{'apiGroups':[''],'resources':['pods'],'verbs':['list','watch']},{'apiGroups':['apps'],'resources':['deployments'],'verbs':['list','watch']}])
    deploy('kube-state-metrics','registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.20.0',8080,args=['--namespaces=lab','--resources=pods,deployments'],user=65534,probe={'httpGet':{'path':'/healthz','port':8080}},sa='kube-state-metrics',limits={'cpu':'500m','memory':'128Mi'})
# Static retained host storage. Only the dedicated kind node receives this
# project-owned host bind mount; PVCs advertise capacity, not a disk quota.
for name,capacity in [('prometheus','3Gi'),('loki','3Gi'),('grafana','1Gi'),('alertmanager','256Mi'),('mailpit','1Gi'),('alloy','256Mi')]:
    pvname='laravel-reliability-'+name
    pv=obj('PersistentVolume',pvname,{'capacity':{'storage':capacity},'accessModes':['ReadWriteOnce'],'persistentVolumeReclaimPolicy':'Retain','storageClassName':'lab-static','hostPath':{'path':'/lab-observability/'+name,'type':'DirectoryOrCreate'},'claimRef':{'namespace':'lab','name':name+'-data'}});pv['metadata'].pop('namespace')
    obj('PersistentVolumeClaim',name+'-data',{'accessModes':['ReadWriteOnce'],'storageClassName':'lab-static','volumeName':pvname,'resources':{'requests':{'storage':capacity}}})
    pod=objects['deployment-'+name]['spec']['template']['spec']
    pod['volumes']=[{'name':'data','persistentVolumeClaim':{'claimName':name+'-data'}} if v['name']=='data' else v for v in pod['volumes']]
    # Local file-based databases/TSDBs must never have two writers on the PVC.
    objects['deployment-'+name]['spec']['strategy']={'type':'Recreate'}
    # New directories from a clean checkout need only project-volume ownership.
    uid=pod['containers'][0]['securityContext']['runAsUser']
    pod.setdefault('initContainers',[]).append({'name':'data-owner','image':'nginx:1.30.5-alpine','imagePullPolicy':'IfNotPresent','command':['sh','-c',f'chown {uid}:{uid} /data && chmod 750 /data'],'resources':{'requests':{'cpu':'10m','memory':'16Mi'},'limits':{'cpu':'100m','memory':'32Mi'}},'volumeMounts':[{'name':'data','mountPath':'/data'}],'securityContext':{'runAsUser':0,'allowPrivilegeEscalation':False,'readOnlyRootFilesystem':True,'capabilities':{'drop':['ALL'],'add':['CHOWN','FOWNER']}}})
objects['deployment-prometheus']['spec']['template']['spec']['containers'][0]['args'].append('--storage.tsdb.retention.size=2GB')

for o in objects.values():
    if o['kind']=='Deployment':
        if o['metadata']['name'] in ['api','worker','scheduler','exporter','simulator']:
            o['spec']['template']['metadata']['annotations']={'lab-source-checksum':simhash if o['metadata']['name']=='simulator' else apphash}
        pod=o['spec']['template']; cfg=[v['configMap']['name'] for v in pod['spec'].get('volumes',[]) if 'configMap' in v]
        if cfg:pod['metadata'].setdefault('annotations',{}).update({'lab-config-checksum':hashlib.sha256(json.dumps([objects['configmap-'+n]['data'] for n in cfg],sort_keys=True).encode()).hexdigest()})
(root/'infra/manifests.json').write_text(json.dumps(objects,indent=2)+'\n')
