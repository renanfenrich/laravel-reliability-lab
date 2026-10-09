from labclient import *
import concurrent.futures,uuid
started=utc(); key='smoke-'+uuid.uuid4().hex
with forward('api',8080) as base:
    assert request(base,'/api/live',auth=False)[0]==200
    assert request(base,'/api/ready',auth=False)[0]==200
    assert request(base,'/api/reports',{'subject':'synthetic-smoke'},auth=False,key=key)[0]==401
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        responses=list(pool.map(lambda _:request(base,'/api/reports',{'subject':'synthetic-smoke'},key=key),range(8)))
    ids={r[1]['id'] for r in responses};assert len(ids)==1,responses
    assert sum(r[0]==202 for r in responses)==1,responses
    id=ids.pop(); result,wait=wait_report(base,id); assert result['state']=='completed' and result['result']['checksum'],result
    row=kube('exec','deployment/postgres','--','psql','-U','lab','-d','lab','-Atc',f"SELECT state,attempts,result->>'checksum' FROM reports WHERE id='{id}'").strip()
    assert row.startswith('completed|1|'),row
save('smoke.json',{'start':started,'end':utc(),'commit':sha(),'concurrent_submissions':8,'unique_report':id,'one_created':True,'database_row':row,'completed_result':result,'completion_wait_seconds':wait,'result':'PASS'})
print('PASS: authenticated committed acceptance, eight concurrent idempotent submissions, worker result and PostgreSQL correlation')
