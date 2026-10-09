<?php
use App\Services\Reports;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;
Artisan::command('lab:reconcile',function(Reports $reports) { $reports->reconcile(); return 0; });
Artisan::command('lab:ready',function() { try { \Illuminate\Support\Facades\DB::select('SELECT 1'); \Illuminate\Support\Facades\Redis::ping(); } catch(\Throwable $e) { return 1; } return 0; });
Schedule::command('lab:reconcile')->everyFiveSeconds()->sendOutputTo('/proc/1/fd/2');
