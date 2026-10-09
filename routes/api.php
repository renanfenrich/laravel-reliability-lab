<?php
use App\Services\Reports;
use App\Services\Metrics;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Route;
Route::get('/live',fn()=>['status'=>'alive']);
Route::get('/ready',function() { try { DB::select('SELECT 1'); Redis::ping(); return ['status'=>'ready']; } catch(\Throwable $e) { return response()->json(['status'=>'unavailable'],503); } });
Route::get('/metrics',fn()=>response(Metrics::render(),200,['Content-Type'=>'text/plain; version=0.0.4']));
Route::middleware(\App\Http\Middleware\LabAuth::class)->group(function() {
    Route::post('/reports',function(Request $r,Reports $reports) {
        $payload=$r->validate(['subject'=>'required|string|regex:/^synthetic-[a-zA-Z0-9_-]+$/|max:80','latency_ms'=>'sometimes|integer|min:0|max:4000','fail_attempts'=>'sometimes|integer|min:0|max:3']);
        $payload=['subject'=>$payload['subject'],'latency_ms'=>$payload['latency_ms']??25,'fail_attempts'=>$payload['fail_attempts']??0];
        abort_if(($payload['latency_ms']!==25 || $payload['fail_attempts']!==0) && ($r->attributes->get('traffic')!=='fault' || !config('lab.faults')),403);
        $key=$r->header('Idempotency-Key'); abort_unless(is_string($key) && preg_match('/^[a-zA-Z0-9_-]{1,128}$/',$key),422,'Idempotency-Key required');
        [$report,$created]=$reports->submit($payload,$key,$r->attributes->get('request_id'),$r->attributes->get('traffic'));
        return response()->json(['id'=>$report['id'],'state'=>$report['state'],'accepted_at'=>$report['accepted_at']],$created?202:200);
    });
    Route::get('/reports/{id}',function(string $id) {
        abort_unless(\Illuminate\Support\Str::isUuid($id),404);
        $r=DB::table('reports')->where('id',$id)->first(); abort_unless($r,404);
        return ['id'=>$r->id,'state'=>$r->state,'attempts'=>$r->attempts,'result'=>$r->result?json_decode($r->result,true):null,'error'=>$r->error,'deadline_met'=>$r->deadline_met,'overdue'=>in_array($r->state,['pending','processing']) && strtotime($r->deadline_at)<time()];
    });
});
