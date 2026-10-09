<?php
namespace App\Services;
use App\Jobs\ProcessReport;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
class Reports {
    public function submit(array $payload, string $key, string $requestId, string $traffic): array {
        $hash=hash('sha256',json_encode($payload));
        $id=(string)Str::uuid();
        $created=DB::transaction(function() use($payload,$key,$requestId,$traffic,$hash,$id) {
            $n=DB::table('reports')->insertOrIgnore(['id'=>$id,'idempotency_key'=>$key,'request_id'=>$requestId,'traffic'=>$traffic,'payload_hash'=>$hash,'payload'=>json_encode($payload),'state'=>'pending','accepted_at'=>now(),'deadline_at'=>now()->addSeconds(60),'dispatch_after'=>now(),'available_at'=>now()]);
            if ($n) Metrics::add('lab_accepted_total',['traffic'=>$traffic]);
            return (bool)$n;
        });
        $report=DB::table('reports')->where('idempotency_key',$key)->first();
        abort_unless(hash_equals($report->payload_hash,$hash) && $report->traffic===$traffic,409,'Idempotency key conflicts with original request');
        if ($created) $this->dispatch($report->id);
        Log::info('report.accepted',['report_id'=>$report->id,'request_id'=>$requestId,'traffic'=>$traffic,'duplicate'=>!$created]);
        return [(array)$report,$created];
    }
    public function dispatch(string $id): void {
        // Record a short dispatch reservation first; a crash or Redis loss is repaired after 5 seconds.
        $n=DB::table('reports')->where('id',$id)->where('state','pending')->where('available_at','<=',now())->where('dispatch_after','<=',now())->update(['dispatch_after'=>now()->addSeconds(5)]);
        if (!$n) return;
        try { ProcessReport::dispatch($id); Metrics::add('lab_dispatch_total',['outcome'=>'queued']); }
        catch (\Throwable $e) { Metrics::add('lab_dispatch_total',['outcome'=>'error']); Log::warning('dispatch.failed',['report_id'=>$id,'exception'=>get_class($e)]); }
    }
    public function reconcile(): void {
        DB::transaction(function() {
            foreach(DB::table('reports')->where('state','processing')->where('lease_until','<=',now())->lockForUpdate()->get() as $r) {
                $state=$r->attempts>=3?'failed':'pending';
                DB::table('reports')->where('id',$r->id)->update(['state'=>$state,'lease_token'=>null,'lease_until'=>null,'dispatch_after'=>now(),'available_at'=>now(),'error'=>'worker lease expired']);
                Metrics::add('lab_lease_recoveries_total',['traffic'=>$r->traffic]);
                if($state==='failed') Metrics::add('lab_failed_total',['traffic'=>$r->traffic]);
                Log::warning('worker.lease_expired',['report_id'=>$r->id,'request_id'=>$r->request_id,'state'=>$state]);
            }
        });
        DB::table('metric_samples')->upsert([['series'=>'lab_scheduler_heartbeat_seconds','value'=>now()->timestamp]],['series'],['value']);
        $this->deadlines();
        foreach(DB::table('reports')->where('state','pending')->where('dispatch_after','<=',now())->limit(500)->pluck('id') as $id) $this->dispatch($id);
    }
    public function deadlines(): void {
        DB::transaction(function() {
            foreach(DB::table('reports')->whereNull('deadline_met')->where('deadline_at','<=',now())->lockForUpdate()->get() as $r) {
                $met=$r->completed_at!==null && strtotime($r->completed_at)<=strtotime($r->deadline_at);
                DB::table('reports')->where('id',$r->id)->update(['deadline_met'=>$met]);
                Metrics::add('lab_deadlines_total',['traffic'=>$r->traffic,'outcome'=>$met?'met':'miss']);
            }
        });
    }
}
