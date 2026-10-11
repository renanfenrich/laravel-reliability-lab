<?php
namespace App\Services;
use Illuminate\Support\Facades\DB;
class Metrics {
    private static function series(string $name, array $labels): string {
        ksort($labels); $parts=[];
        foreach ($labels as $k=>$v) $parts[]=$k.'="'.addcslashes((string)$v,"\\\"\n").'"';
        return $name.($parts ? '{'.implode(',',$parts).'}' : '');
    }
    private static function increments(array $samples): void {
        // One atomic statement, with stable lock order for concurrent histogram writers.
        ksort($samples); $bindings=[];
        foreach ($samples as $series=>$value) { $bindings[]=$series; $bindings[]=$value; }
        DB::statement('INSERT INTO metric_samples(series,value) VALUES '.implode(',',array_fill(0,count($samples),'(?,?)')).' ON CONFLICT(series) DO UPDATE SET value=metric_samples.value+EXCLUDED.value',$bindings);
    }
    public static function add(string $name, array $labels=[], float $value=1): void {
        self::increments([self::series($name,$labels)=>$value]);
    }
    public static function observe(string $name, float $value, array $labels, array $buckets): void {
        $samples=[];
        foreach ($buckets as $b) if ($value <= $b) $samples[self::series($name.'_bucket',array_merge($labels,['le'=>(string)$b]))]=1;
        $samples[self::series($name.'_bucket',array_merge($labels,['le'=>'+Inf']))]=1;
        $samples[self::series($name.'_count',$labels)]=1;
        $samples[self::series($name.'_sum',$labels)]=$value;
        self::increments($samples);
    }
    public static function render(): string {
        $defaults=[];
        $zero=function($name,$labels=[]) use (&$defaults) { ksort($labels); $parts=[]; foreach($labels as $k=>$v) $parts[]=$k.'="'.$v.'"'; $defaults[$name.($parts?'{'.implode(',',$parts).'}':'')]=0; };
        foreach(['normal','load','fault'] as $traffic) {
            foreach(['accepted','completed','failed','attempts','retries','lease_recoveries'] as $m) $zero('lab_'.$m.'_total',['traffic'=>$traffic]);
            foreach(['met','miss'] as $outcome) $zero('lab_deadlines_total',compact('traffic','outcome'));
            foreach(['submit','status'] as $route) foreach(['2xx','5xx'] as $class) {
                $labels=compact('traffic','route','class'); $zero('lab_http_total',$labels);
                foreach([0.05,0.1,0.25,0.5,1,2,5,'+Inf'] as $le) $zero('lab_http_seconds_bucket',array_merge($labels,['le'=>$le]));
                $zero('lab_http_seconds_count',$labels); $zero('lab_http_seconds_sum',$labels);
            }
            foreach(['success','error'] as $outcome) {
                $labels=compact('traffic','outcome');
                foreach([0.1,0.5,1,3,5,'+Inf'] as $le) $zero('lab_external_seconds_bucket',array_merge($labels,['le'=>$le]));
                $zero('lab_external_seconds_count',$labels); $zero('lab_external_seconds_sum',$labels);
            }
            foreach([1,5,15,30,60,120,'+Inf'] as $le) $zero('lab_processing_seconds_bucket',['traffic'=>$traffic,'le'=>$le]);
            $zero('lab_processing_seconds_count',['traffic'=>$traffic]); $zero('lab_processing_seconds_sum',['traffic'=>$traffic]);
        }
        foreach(['queued','error'] as $outcome) $zero('lab_dispatch_total',['outcome'=>$outcome]);
        $zero('lab_scheduler_heartbeat_seconds');
        foreach(DB::table('metric_samples')->get() as $sample) $defaults[$sample->series]=$sample->value;
        $lines=[];
        foreach(['http','external','processing'] as $h) $lines[]='# TYPE lab_'.$h.'_seconds histogram';
        foreach($defaults as $series=>$value) $lines[]=$series.' '.$value;
        foreach (['normal','load','fault'] as $traffic) {
            foreach (['pending','processing','completed','failed'] as $state) {
                $lines[]='lab_reports{traffic="'.$traffic.'",state="'.$state.'"} '.DB::table('reports')->where(compact('traffic','state'))->count();
            }
            $lines[]='lab_overdue_reports{traffic="'.$traffic.'"} '.DB::table('reports')->where('traffic',$traffic)->whereIn('state',['pending','processing'])->where('deadline_at','<=',now())->count();
        }
        foreach(['5m'=>300,'30m'=>1800,'1h'=>3600,'2h'=>7200,'6h'=>21600,'1d'=>86400,'3d'=>259200,'30d'=>2592000] as $window=>$seconds) {
            foreach(['normal','load','fault'] as $traffic) {
                $q=DB::table('reports')->where('traffic',$traffic)->where('deadline_at','<=',now())->where('deadline_at','>',now()->subSeconds($seconds));
                $lines[]='lab_processing_cohort_total{traffic="'.$traffic.'",window="'.$window.'"} '.(clone $q)->count();
                $lines[]='lab_processing_cohort_met{traffic="'.$traffic.'",window="'.$window.'"} '.(clone $q)->whereNotNull('completed_at')->whereColumn('completed_at','<=','deadline_at')->count();
            }
        }
        // Native cumulative DB statistics; one authoritative exporter, no raw SQL labels.
        $stats=DB::selectOne('SELECT xact_commit,xact_rollback,blks_read,blks_hit,deadlocks FROM pg_stat_database WHERE datname=current_database()');
        foreach ((array)$stats as $kind=>$value) $lines[]='lab_postgres_stat_total{kind="'.$kind.'"} '.$value;
        $waits=DB::select("SELECT CASE WHEN query ILIKE '%metric_samples%' THEN 'metrics' WHEN query ILIKE '%reports%' THEN 'reports' ELSE 'other' END AS operation, CASE WHEN wait_event_type IN ('Lock','IO','Client') THEN wait_event_type WHEN wait_event_type IS NULL THEN 'running' ELSE 'other' END AS wait_type,count(*) AS sessions FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND state<>'idle' GROUP BY 1,2");
        $sessions=[];
        foreach ($waits as $w) $sessions[$w->operation][$w->wait_type]=$w->sessions;
        foreach (['metrics','reports','other'] as $operation) foreach (['Lock','IO','Client','running','other'] as $type) $lines[]='lab_postgres_sessions{operation="'.$operation.'",wait_type="'.$type.'"} '.($sessions[$operation][$type]??0);
        $lines[]='lab_redis_queue_jobs '.\Illuminate\Support\Facades\Redis::llen('queues:reports');
        $lines[]='lab_telemetry_heartbeat_seconds '.time();
        return implode("\n",$lines)."\n";
    }
}
