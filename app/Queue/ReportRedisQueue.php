<?php
namespace App\Queue;
use App\Jobs\ProcessReport;
use App\Services\Metrics;
use Illuminate\Queue\RedisQueue;
use Illuminate\Support\Facades\Redis;
class ReportRedisQueue extends RedisQueue {
    protected function createPayloadArray($job, $queue, $data='') {
        if (!$job instanceof ProcessReport) return parent::createPayloadArray($job,$queue,$data);
        $job->notificationKey='lab:notification:'.$queue.':'.$job->reportId;
        return array_merge(parent::createPayloadArray($job,$queue,$data),[
            'notification_key'=>$job->notificationKey,'notification_token'=>$job->notificationToken,
        ]);
    }
    public function pushRaw($payload, $queue=null, array $options=[]) {
        $data=json_decode($payload,true,512,JSON_THROW_ON_ERROR);
        if (!isset($data['notification_key'],$data['notification_token'])) return parent::pushRaw($payload,$queue,$options);
        $key=$this->getQueue($queue);
        $added=$this->getConnection()->eval(<<<'LUA'
if redis.call('EXISTS',KEYS[3]) == 1 then return 0 end
-- Redis scripts isolate concurrent operations but do not roll back runtime errors.
for i=1,2 do
    local kind=redis.call('TYPE',KEYS[i]).ok
    if kind ~= 'none' and kind ~= 'list' then return redis.error_reply('Invalid queue key type') end
end
redis.call('RPUSH',KEYS[1],ARGV[1])
redis.call('RPUSH',KEYS[2],1)
redis.call('SET',KEYS[3],ARGV[2],'EX',86400)
return 1
LUA,3,$key,$key.':notify',$data['notification_key'],$payload,$data['notification_token']);
        Metrics::add('lab_dispatch_total',['outcome'=>$added?'queued':'suppressed']);
        return $added ? $data['id'] : null;
    }
    public static function releaseGuard(string $key, string $token, string $connection='default'): void {
        if ($key==='' || $token==='') return; // Legacy payloads/direct test execution carry no guard.
        Redis::connection($connection)->eval(<<<'LUA'
if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end
return 0
LUA,1,$key,$token);
    }
}
