#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent.parent
objects={}
def source_hash(dirs,files):
    paths=[root/f for f in files]
    for d in dirs:paths.extend((root/d).rglob('*.php'))
    data=b''.join(str(f.relative_to(root)).encode()+b'\0'+f.read_bytes() for f in sorted(paths) if f.is_file() and 'cache' not in f.parts)
    return hashlib.sha256(data).hexdigest()
apphash=source_hash(['app','bootstrap','config','database','routes','public'],['Dockerfile','.dockerignore','composer.json','composer.lock','artisan'])
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
    pod={'containers':[c],'terminationGracePeriodSeconds':25,'automountServiceAccountToken':bool(sa),'securityContext':{'seccompProfile':{'type':'RuntimeDefault'}},'volumes':volumes or []}
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
deploy('simulator','laravel-reliability-simulator:g1',8081,probe={'httpGet':{'path':'/live','port':8081}},limits={'cpu':'1','memory':'128Mi'})
appenv=[secret(n) for n in ['APP_KEY','DB_PASSWORD','REDIS_PASSWORD','LAB_TOKEN']]+[{'name':'APP_ENV','value':'local'},{'name':'LAB_FAULTS','value':'true'},{'name':'DB_HOST','value':'postgres'},{'name':'REDIS_HOST','value':'redis'},{'name':'SIMULATOR_URL','value':'http://simulator:8081'}]
vols=[{'name':n,'emptyDir':{}} for n in ['storage','cache','tmp']]
mounts=[{'name':'storage','mountPath':'/app/storage'},{'name':'cache','mountPath':'/app/bootstrap/cache'},{'name':'tmp','mountPath':'/tmp'}]
# Mounting empty storage requires framework directories before application boot.
init=[{'name':'storage-init','image':'laravel-reliability-app:g1','imagePullPolicy':'IfNotPresent','command':['sh','-c','mkdir -p /app/storage/framework/cache /app/storage/framework/views /app/storage/framework/sessions /app/storage/logs'],'volumeMounts':mounts,'securityContext':{'runAsUser':1000,'runAsNonRoot':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}}]
for name in ['api','worker','scheduler','exporter']:
    cmd=['php','-S','0.0.0.0:8080','-t','public','public/index.php'] if name in ['api','exporter'] else ['php','artisan']+(['queue:work','redis','--queue=reports','--sleep=1','--timeout=10','--tries=1'] if name=='worker' else ['schedule:work'])
    env=appenv+[{'name':'LAB_ROLE','value':name}]
    if name=='api':env+=[{'name':'PHP_CLI_SERVER_WORKERS','value':'4'}]
    probe={'httpGet':{'path':'/api/ready','port':8080}} if name in ['api','exporter'] else {'exec':{'command':['php','artisan','lab:ready']}}
    deploy(name,'laravel-reliability-app:g1',8080,command=cmd,env=env,volumes=vols,mounts=mounts,replicas=2 if name in ['api','worker'] else 1,probe=probe,init=init)
    c=objects['deployment-'+name]['spec']['template']['spec']['containers'][0]
    c['livenessProbe']={'httpGet':{'path':'/api/live','port':8080},'periodSeconds':10,'failureThreshold':3} if name in ['api','exporter'] else {'exec':{'command':['php','-r',"exit(str_contains(file_get_contents('/proc/1/cmdline'), 'artisan') ? 0 : 1);"]},'periodSeconds':10,'failureThreshold':3}

if (root/'observability/prometheus.yml').exists():
    config('prometheus',{'prometheus.yml':(root/'observability/prometheus.yml').read_text(),'rules.yml':(root/'observability/rules.yml').read_text()})
    v,m=configvol('prometheus','/etc/prometheus'); deploy('prometheus','prom/prometheus:v3.15.0',9090,args=['--config.file=/etc/prometheus/prometheus.yml','--storage.tsdb.path=/prometheus','--storage.tsdb.retention.time=31d'],volumes=[v,{'name':'data','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/prometheus'}],user=65534,probe={'httpGet':{'path':'/-/ready','port':9090}},limits={'cpu':'2','memory':'768Mi'},sa='prometheus')
    role('prometheus',[{'apiGroups':[''],'resources':['nodes'],'verbs':['get','list','watch']},{'apiGroups':[''],'resources':['nodes/metrics'],'verbs':['get']}],True)
    config('loki',{'loki.yml':(root/'observability/loki.yml').read_text()})
    v,m=configvol('loki','/etc/loki');deploy('loki','grafana/loki:3.7.8',3100,args=['-config.file=/etc/loki/loki.yml'],volumes=[v,{'name':'data','emptyDir':{}},{'name':'tmp','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/loki'},{'name':'tmp','mountPath':'/tmp'}],user=10001,probe={'httpGet':{'path':'/ready','port':3100}},limits={'cpu':'1','memory':'512Mi'})
    config('alloy',{'config.alloy':(root/'observability/config.alloy').read_text()})
    v,m=configvol('alloy','/etc/alloy');deploy('alloy','grafana/alloy:v1.20.1',12345,args=['run','/etc/alloy/config.alloy','--server.http.listen-addr=0.0.0.0:12345','--storage.path=/alloy'],volumes=[v,{'name':'data','emptyDir':{}}],mounts=[m,{'name':'data','mountPath':'/alloy'}],user=1000,probe={'httpGet':{'path':'/-/ready','port':12345}},sa='alloy',limits={'cpu':'1','memory':'256Mi'})
    role('alloy',[{'apiGroups':[''],'resources':['pods'],'verbs':['get','list','watch']},{'apiGroups':[''],'resources':['pods/log'],'verbs':['get']}])
    config('grafana-datasources',{'datasources.yml':(root/'observability/datasources.yml').read_text()})
    config('grafana-provider',{'dashboards.yml':(root/'observability/dashboards.yml').read_text()})
    config('grafana-dashboard',{'lab.json':(root/'observability/dashboard.json').read_text()})
    pairs=[configvol(n,path) for n,path in [('grafana-datasources','/etc/grafana/provisioning/datasources'),('grafana-provider','/etc/grafana/provisioning/dashboards'),('grafana-dashboard','/var/lib/grafana/dashboards')]]
    deploy('grafana','grafana/grafana:13.2.3',3000,env=[secret('GF_SECURITY_ADMIN_USER'),secret('GF_SECURITY_ADMIN_PASSWORD'),{'name':'GF_ANALYTICS_REPORTING_ENABLED','value':'false'},{'name':'GF_ANALYTICS_CHECK_FOR_UPDATES','value':'false'}],volumes=[x[0] for x in pairs]+[{'name':'data','emptyDir':{}},{'name':'tmp','emptyDir':{}}],mounts=[x[1] for x in pairs]+[{'name':'data','mountPath':'/var/lib/grafana'},{'name':'tmp','mountPath':'/tmp'}],user=472,probe={'httpGet':{'path':'/api/health','port':3000}},limits={'cpu':'1','memory':'512Mi'})
    role('kube-state-metrics',[{'apiGroups':[''],'resources':['pods'],'verbs':['list','watch']},{'apiGroups':['apps'],'resources':['deployments'],'verbs':['list','watch']}])
    deploy('kube-state-metrics','registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.20.0',8080,args=['--namespaces=lab','--resources=pods,deployments'],user=65534,probe={'httpGet':{'path':'/healthz','port':8080}},sa='kube-state-metrics',limits={'cpu':'500m','memory':'128Mi'})
for o in objects.values():
    if o['kind']=='Deployment':
        if o['metadata']['name'] in ['api','worker','scheduler','exporter','simulator']:
            o['spec']['template']['metadata']['annotations']={'lab-source-checksum':simhash if o['metadata']['name']=='simulator' else apphash}
        pod=o['spec']['template']; cfg=[v['configMap']['name'] for v in pod['spec'].get('volumes',[]) if 'configMap' in v]
        if cfg:pod['metadata'].setdefault('annotations',{}).update({'lab-config-checksum':hashlib.sha256(json.dumps([objects['configmap-'+n]['data'] for n in cfg],sort_keys=True).encode()).hexdigest()})
(root/'infra/manifests.json').write_text(json.dumps(objects,indent=2)+'\n')
