<?php
namespace App\Jobs;
use App\Services\Metrics;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
class ProcessReport implements ShouldQueue {
    use Queueable;
    public int $tries=1; public int $timeout=10;
    public string $notificationKey=''; public string $notificationToken='';
    public function __construct(public string $reportId) { $this->notificationToken=(string)Str::uuid(); }
    public function handle(): void {
        $token=(string)Str::uuid();
        $r=DB::transaction(function() use($token) {
            $r=DB::table('reports')->where('id',$this->reportId)->lockForUpdate()->first();
            if(!$r || $r->state!=='pending' || strtotime($r->available_at)>now()->timestamp) return null;
            if($r->attempts>=3) return null;
            DB::table('reports')->where('id',$r->id)->update(['state'=>'processing','attempts'=>$r->attempts+1,'lease_token'=>$token,'lease_until'=>now()->addSeconds(15)]);
            $r->attempts++; Metrics::add('lab_attempts_total',['traffic'=>$r->traffic]); return $r;
        });
        // SQL claim/no-op is committed before clearing only this delivery's guard.
        \App\Queue\ReportRedisQueue::releaseGuard($this->notificationKey,$this->notificationToken);
        if(!$r) return;
        Log::info('report.processing',['report_id'=>$r->id,'request_id'=>$r->request_id,'attempt'=>$r->attempts]);
        $start=microtime(true); $error=null; $result=null;
        try { $result=Http::connectTimeout(1)->timeout(5)->withHeaders(['X-Request-ID'=>$r->request_id])->post(config('lab.simulator').'/process',['report_id'=>$r->id,'attempt'=>$r->attempts,'payload'=>json_decode($r->payload,true)])->throw()->json(); if(!isset($result['checksum'])) throw new \RuntimeException('Invalid simulator response'); }
        catch(\Throwable $e) { $error=get_class($e); }
        DB::transaction(function() use($r,$token,$result,$error,$start) {
            $current=DB::table('reports')->where('id',$r->id)->lockForUpdate()->first();
            if($current->state!=='processing' || $current->lease_token!==$token) return;
            Metrics::observe('lab_external_seconds',microtime(true)-$start,['traffic'=>$r->traffic,'outcome'=>$error?'error':'success'],[0.1,0.5,1,3,5]);
            $state=$error?($r->attempts>=3?'failed':'pending'):'completed';
            DB::table('reports')->where('id',$r->id)->update(['state'=>$state,'result'=>$result?json_encode($result):null,'completed_at'=>$state==='completed'?now()->format('Y-m-d H:i:s.uP'):null,'error'=>$error,'lease_token'=>null,'lease_until'=>null,'dispatch_after'=>now()->addSeconds(2**$r->attempts),'available_at'=>now()->addSeconds(2**$r->attempts)]);
            if($state==='completed') { Metrics::add('lab_completed_total',['traffic'=>$r->traffic]); Metrics::observe('lab_processing_seconds',(float)now()->format('U.u')-(float)\Illuminate\Support\Carbon::parse($r->accepted_at)->format('U.u'),['traffic'=>$r->traffic],[1,5,15,30,60,120]); }
            elseif($state==='failed') Metrics::add('lab_failed_total',['traffic'=>$r->traffic]);
            else Metrics::add('lab_retries_total',['traffic'=>$r->traffic]);
            Log::info('report.'.$state,['report_id'=>$r->id,'request_id'=>$r->request_id,'attempt'=>$r->attempts,'error'=>$error]);
        });
    }
}
