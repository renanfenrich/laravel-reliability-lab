<?php
namespace App\Providers;
use App\Queue\ReportRedisConnector;
use App\Queue\ReportRedisQueue;
use App\Services\Metrics;
use Illuminate\Support\Facades\Log;
use Illuminate\Queue\Events\JobFailed;
use Illuminate\Support\ServiceProvider;
class QueueServiceProvider extends ServiceProvider {
    public function register(): void {
        $this->app->afterResolving('queue',function($manager) {
            $manager->addConnector('report-redis',fn()=>new ReportRedisConnector($this->app['redis']));
        });
    }
    public function boot(): void {
        // A reserved delivery can exhaust transport attempts before handle runs.
        $this->app['events']->listen(JobFailed::class,function(JobFailed $event) {
            $payload=$event->job->payload();
            ReportRedisQueue::releaseGuard($payload['notification_key']??'',$payload['notification_token']??'',
                config('queue.connections.'.$event->connectionName.'.connection','default'));
            if (isset($payload['report_id'])) {
                Metrics::add('lab_notification_failures_total');
                Log::warning('notification.transport_failed',['report_id'=>$payload['report_id'],'queue_attempts'=>$event->job->attempts(),'exception'=>get_class($event->exception)]);
            }
        });
    }
}
