<?php
namespace App\Http\Middleware;
use App\Services\Metrics;
use Illuminate\Contracts\Debug\ExceptionHandler;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
class Observe {
    public function handle($request, \Closure $next) {
        $id=$request->header('X-Request-ID');
        if(!is_string($id) || !preg_match('/^[a-zA-Z0-9_-]{1,64}$/',$id)) $id=(string)Str::uuid();
        $request->attributes->set('request_id',$id); $start=microtime(true);
        try { $response=$next($request); } catch(\Throwable $e) { $response=app(ExceptionHandler::class)->render($request,$e); }
        $route=$request->route()?->uri(); $status=$response->getStatusCode();
        $traffic=$request->attributes->get('traffic','normal');
        if(in_array($route,['api/reports','api/reports/{id}']) && ($status<400 || $status>=500)) {
            try { \Illuminate\Support\Facades\DB::transaction(function() use($route,$status,$traffic,$start) {
                $labels=['route'=>$route==='api/reports'?'submit':'status','traffic'=>$traffic,'class'=>(string)intdiv($status,100).'xx'];
                Metrics::add('lab_http_total',$labels);
                Metrics::observe('lab_http_seconds',microtime(true)-$start,$labels,[0.05,0.1,0.25,0.5,1,2,5]);
            }); } catch(\Throwable $e) { Log::error('telemetry.write_failed',['request_id'=>$id]); }
        }
        Log::info('http.response',['request_id'=>$id,'route'=>$route,'status'=>$status,'traffic'=>$traffic,'duration_seconds'=>microtime(true)-$start]);
        $response->headers->set('X-Request-ID',$id); return $response;
    }
}
