<?php
require '/app/vendor/autoload.php';
$app=require '/app/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
use Illuminate\Support\Facades\DB;
use App\Services\Metrics;
if (config('database.connections.pgsql.database') !== 'lab_test') { fwrite(STDERR, 'Benchmark requires isolated lab_test database'.PHP_EOL); exit(1); }
DB::table('metric_samples')->where('series','like','lab_benchmark_%')->delete();
$queries=0;$sqlMs=0;
DB::listen(function($q) use (&$queries,&$sqlMs) { $queries++;$sqlMs+=$q->time; });
$begin=microtime(true);
for($i=0;$i<500;$i++) DB::transaction(fn()=>Metrics::observe('lab_benchmark_seconds',0.025,['traffic'=>'load'],[.05,.1,.25,.5,1,2,5]));
echo json_encode(['observations'=>500,'sql_statements'=>$queries,'sql_ms'=>$sqlMs,'elapsed_seconds'=>microtime(true)-$begin,'series'=>DB::table('metric_samples')->where('series','like','lab_benchmark_%')->get()]),PHP_EOL;
DB::table('metric_samples')->where('series','like','lab_benchmark_%')->delete();
