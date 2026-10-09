<?php
namespace App\Http\Middleware;
use Illuminate\Http\Request;
use Closure;
class LabAuth { public function handle(Request $r,Closure $next) {
    abort_unless(config('lab.token') && hash_equals(config('lab.token'),$r->bearerToken()??''),401);
    $traffic=$r->header('X-Lab-Traffic','normal'); abort_unless(in_array($traffic,['normal','load','fault']),422);
    abort_if($traffic==='fault' && !config('lab.faults'),403); $r->attributes->set('traffic',$traffic); return $next($r);

}}
