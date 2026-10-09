from pathlib import Path
import contextlib,json,os,socket,subprocess,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent.parent
ENV=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line)
K=[str(ROOT/'.tools/kubectl'),'--kubeconfig',str(ROOT/'.kubeconfig'),'--context','kind-laravel-reliability-lab','-n','lab']
def kube(*args):return subprocess.check_output(K+list(args),text=True)
def sha():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def utc():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def request(base,path,body=None,traffic='normal',key=None,auth=True):
    headers={'Content-Type':'application/json','X-Lab-Traffic':traffic}
    if auth:headers['Authorization']='Bearer '+ENV['LAB_TOKEN']
    if key:headers['Idempotency-Key']=key
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return r.status,json.loads(r.read()),time.monotonic()-start
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read()),time.monotonic()-start
@contextlib.contextmanager
def forward(service,remote):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    proc=subprocess.Popen(K+['port-forward','--address=127.0.0.1','service/'+service,f'{port}:{remote}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(150):
            if proc.poll() is not None:raise RuntimeError('port-forward failed: '+service)
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.2):break
            except OSError:time.sleep(.2)
        else:raise TimeoutError(service)
        yield f'http://127.0.0.1:{port}'
    finally:proc.terminate();proc.wait(timeout=5)
def wait_report(base,id,timeout=90,traffic="normal"):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        code,r,_=request(base,'/api/reports/'+id,traffic=traffic)
        assert code==200,r
        if r['state'] in ['completed','failed']:return r,time.monotonic()-start
        time.sleep(.25)
    raise TimeoutError(id)
def save(name,data):
    p=ROOT/'evidence'/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')
