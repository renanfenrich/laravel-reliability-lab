#!/usr/bin/env python3
import ipaddress,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
UNIT='laravel-reliability-lab-host-metrics.service'
if sys.argv[1]=='stop':
 subprocess.run(['systemctl','--user','stop',UNIT],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
else:
 node=json.loads(subprocess.check_output(['docker','inspect','laravel-reliability-lab-control-plane'],text=True))[0]
 gateway=node['NetworkSettings']['Networks']['kind']['Gateway'];assert ipaddress.ip_address(gateway).is_private
 (ROOT/'.runtime').mkdir(exist_ok=True)
 (ROOT/'.runtime/host-metrics-address').write_text(gateway+'\n')
 subprocess.run(['systemctl','--user','stop',UNIT],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(['systemd-run','--user','--unit='+UNIT.removesuffix('.service'),'--property=Restart=always','--property=RestartSec=3','--property=MemoryMax=128M','--setenv=PATH='+os.environ['PATH'],sys.executable,str(ROOT/'scripts/host-metrics.py'),'--bind',gateway],check=True)
 print('Host metrics bound only to kind bridge '+gateway+':19100')
