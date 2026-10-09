<?php
namespace App\Services;
use Illuminate\Support\Facades\DB;
class Metrics {
    public static function add(string $name, array $labels=[], float $value=1): void {
        ksort($labels); $parts=[];
        foreach ($labels as $k=>$v) $parts[]=$k.'="'.addcslashes((string)$v,"\\\"\n").'"';
        $series=$name.($parts ? '{'.implode(',',$parts).'}' : '');
        DB::statement('INSERT INTO metric_samples(series,value) VALUES (?,?) ON CONFLICT(series) DO UPDATE SET value=metric_samples.value+EXCLUDED.value',[$series,$value]);
    }
    public static function observe(string $name, float $value, array $labels, array $buckets): void {
        foreach ($buckets as $b) if ($value <= $b) self::add($name.'_bucket',array_merge($labels,['le'=>(string)$b]));
        self::add($name.'_bucket',array_merge($labels,['le'=>'+Inf']));
        self::add($name.'_count',$labels); self::add($name.'_sum',$labels,$value);
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
        $lines[]='lab_telemetry_heartbeat_seconds '.time();
        return implode("\n",$lines)."\n";
    }
}
