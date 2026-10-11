<?php
namespace App\Providers;
use App\Queue\ReportRedisConnector;
use App\Queue\ReportRedisQueue;
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
        });
    }
}
