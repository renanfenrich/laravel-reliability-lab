<?php
namespace App\Queue;
use Illuminate\Queue\Connectors\RedisConnector;
class ReportRedisConnector extends RedisConnector {
    public function connect(array $config) {
        return new ReportRedisQueue($this->redis,$config['queue'],$config['connection']??$this->connection,
            $config['retry_after']??20,$config['block_for']??1,$config['after_commit']??true,$config['migration_batch_size']??-1);
    }
}
