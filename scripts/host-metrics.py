#!/usr/bin/env python3
"""Local Linux/Docker read-only collector; Docker socket is never exposed to pods."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
ROOT=Path(__file__).resolve().parent.parent
PROJECT='laravel-reliability-lab'

def command(*args):return subprocess.check_output(args,text=True,timeout=12)
def quantity(text):
 m=re.fullmatch(r'([0-9.]+)\s*([kMGT]?i?B)',text.strip())
 if not m:raise ValueError(text)
 units={'B':1,'kB':1000,'MB':1000**2,'GB':1000**3,'TB':1000**4,'KiB':1024,'MiB':1024**2,'GiB':1024**3,'TiB':1024**4}
 return float(m[1])*units[m[2]]
def allowed(name):return name==PROJECT+'-control-plane' or re.fullmatch(PROJECT+r'-(api|http|worker|scheduler|simulator|postgres|redis)-\d+',name) is not None

def collect():
 lines=[]
 def emit(name,value,labels=None,kind='gauge'):
  labels=labels or {};label='{'+','.join(k+'='+json.dumps(str(v)) for k,v in labels.items())+'}' if labels else ''
  if not any(l.startswith('# TYPE '+name+' ') for l in lines):lines.extend(['# HELP '+name+' Local lab host or selected project Docker measurement.','# TYPE '+name+' '+kind])
  lines.append(name+label+' '+str(value))
 hz=os.sysconf('SC_CLK_TCK')
 for row in Path('/proc/stat').read_text().splitlines():
  fields=row.split()
  if fields and re.fullmatch(r'cpu\d+',fields[0]):
   for mode,value in zip(['user','nice','system','idle','iowait','irq','softirq','steal'],fields[1:9]):emit('lab_host_cpu_seconds_total',int(value)/hz,{'cpu':fields[0],'mode':mode},'counter')
 for key,value in (r.split(':',1) for r in Path('/proc/meminfo').read_text().splitlines()):
  if key in ['MemTotal','MemAvailable','SwapTotal','SwapFree']:emit('lab_host_memory_bytes',int(value.split()[0])*1024,{'kind':key})
 for i,value in enumerate(os.getloadavg()):emit('lab_host_load',value,{'minutes':[1,5,15][i]})
 emit('lab_host_cpu_count',os.cpu_count())
 emit('lab_host_uptime_seconds',float(Path('/proc/uptime').read_text().split()[0]))
 disk=os.statvfs(ROOT)
 emit('lab_host_filesystem_size_bytes',disk.f_blocks*disk.f_frsize)
 emit('lab_host_filesystem_available_bytes',disk.f_bavail*disk.f_frsize)
 emit('lab_host_filesystem_inodes_free',disk.f_favail)
 emit('lab_host_filesystem_inodes_total',disk.f_files)
 for row in Path('/proc/net/dev').read_text().splitlines()[2:]:
  interface,raw=row.split(':');interface=interface.strip()
  if not (Path('/sys/class/net')/interface/'device').exists():continue
  f=list(map(int,raw.split()))
  for name,pos in [('receive_bytes',0),('receive_errors',2),('receive_drops',3),('transmit_bytes',8),('transmit_errors',10),('transmit_drops',11)]:emit('lab_host_network_'+name+'_total',f[pos],{'interface':interface},'counter')
 for row in Path('/proc/diskstats').read_text().splitlines():
  f=row.split();device=f[2]
  if not (Path('/sys/block')/device/'device').exists():continue
  for name,value in [('read_bytes',int(f[5])*512),('written_bytes',int(f[9])*512),('io_seconds',int(f[12])/1000)]:emit('lab_host_disk_'+name+'_total',value,{'device':device},'counter')
 try:
  names=[n for n in command('docker','ps','--format','{{.Names}}').splitlines() if allowed(n)]
  stats=command('docker','stats','--no-stream','--format','{{json .}}',*names) if names else ''
  for row in stats.splitlines():
   s=json.loads(row);name=s['Name'];assert allowed(name)
   labels={'container':name,'scope':'kind-node' if name.endswith('-control-plane') else 'compose'}
   emit('lab_docker_cpu_cores',float(s['CPUPerc'].rstrip('%'))/100,labels)
   memory=[quantity(x) for x in s['MemUsage'].split('/')]
   emit('lab_docker_memory_used_bytes',memory[0],labels);emit('lab_docker_memory_limit_bytes',memory[1],labels)
   emit('lab_docker_pids',int(s['PIDs']),labels)
   for field,prefix,directions in [('NetIO','network',['receive','transmit']),('BlockIO','block',['read','write'])]:
    for direction,value in zip(directions,s[field].split('/')):emit('lab_docker_'+prefix+'_'+direction+'_bytes_total',quantity(value),labels,'counter')
  emit('lab_host_docker_collection_success',1)
 except (subprocess.SubprocessError,ValueError,KeyError) as err:
  print(json.dumps({'event':'docker_collection_failed','error':type(err).__name__}),flush=True);emit('lab_host_docker_collection_success',0)
 emit('lab_host_collection_timestamp_seconds',time.time())
 return '\n'.join(lines)+'\n'

class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path!='/metrics':self.send_error(404);return
  try:body=collect().encode()
  except Exception as err:print(type(err).__name__,flush=True);self.send_error(503);return
  self.send_response(200);self.send_header('Content-Type','text/plain; version=0.0.4');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bind');p.add_argument('--test',action='store_true');args=p.parse_args()
 if args.test:
  assert quantity('2.352MiB')==2.352*1024**2 and quantity('1.16GB')==1.16e9
  assert allowed(PROJECT+'-http-1') and allowed(PROJECT+'-api-1') and allowed(PROJECT+'-control-plane')
  assert not allowed('unrelated-api-1') and not allowed(PROJECT+'-api-run-random')
  body=collect();assert 'lab_host_cpu_seconds_total' in body and 'lab_host_docker_collection_success 1' in body
  print('PASS: units, project-only Docker selection and actual collection')
 else:
  if not args.bind:p.error('--bind must be the dedicated kind bridge gateway')
  HTTPServer((args.bind,19100),Handler).serve_forever()
