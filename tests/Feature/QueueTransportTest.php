<?php
namespace Tests\Feature;
use App\Services\Reports;
use App\Queue\ReportRedisQueue;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Str;
use Tests\TestCase;
class QueueTransportTest extends TestCase {
    use DatabaseMigrations;
    private string $queue; private array $ids=[]; private $transport;
    protected function setUp(): void {
        parent::setUp();
        $this->assertSame(15,config('database.redis.default.database'));
        $this->queue='g4-test-'.Str::uuid();
        config(['queue.connections.redis.queue'=>$this->queue]);
        $this->transport=Queue::connection('redis');
    }
    protected function tearDown(): void {
        if (isset($this->queue)) {
            $keys=['queues:'.$this->queue,'queues:'.$this->queue.':notify','queues:'.$this->queue.':reserved','queues:'.$this->queue.':delayed'];
            foreach($this->ids as $id) $keys[]=$this->guard($id);
            Redis::del(...$keys); // Only this test's unique queue/owned guards in database 15.
        }
        parent::tearDown();
    }
    private function guard(string $id): string { return 'lab:notification:queues:'.$this->queue.':'.$id; }
    private function accept(): string {
        $r=$this->withToken('synthetic-test-only')->withHeader('Idempotency-Key','g4-test-'.Str::uuid())->postJson('/api/reports',['subject'=>'synthetic-transport']);
        $id=$r->assertStatus(202)->json('id');$this->ids[]=$id;return $id;
    }
    private function finish(): void {
        Http::fake(['*'=>Http::response(['checksum'=>'synthetic-transport'],200)]);
        $job=$this->transport->pop();$this->assertNotNull($job);$job->fire();
    }
    public function test_waiting_notification_is_not_amplified_by_reconciliation(): void {
        $id=$this->accept();
        for($i=0;$i<6;$i++) { $this->travel(6)->seconds();app(Reports::class)->reconcile(); }
        $this->assertSame(1,$this->transport->size());
        $this->assertEquals(1,DB::table('metric_samples')->where('series','lab_dispatch_total{outcome="queued"}')->value('value'));
        $this->assertEquals(6,DB::table('metric_samples')->where('series','lab_dispatch_total{outcome="suppressed"}')->value('value'));
        $this->finish();$this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed','attempts'=>1]);
        $this->assertSame(0,$this->transport->size());$this->assertNull(Redis::get($this->guard($id)));
    }
    public function test_predictable_enqueue_error_does_not_strand_a_guard(): void {
        Redis::set('queues:'.$this->queue,'synthetic-wrong-type');
        $id=$this->accept();$this->assertNull(Redis::get($this->guard($id)));
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'pending']);
        Redis::del('queues:'.$this->queue);$this->travel(6)->seconds();app(Reports::class)->reconcile();
        $this->finish();$this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed']);
    }
    public function test_isolated_transport_state_loss_recovers_committed_acceptance(): void {
        $id=$this->accept();
        Redis::del('queues:'.$this->queue,'queues:'.$this->queue.':notify',$this->guard($id));
        $this->travel(6)->seconds();app(Reports::class)->reconcile();
        $this->assertSame(1,$this->transport->size());$this->finish();
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed','attempts'=>1]);
    }
    public function test_stale_delivery_cannot_release_a_newer_notification_guard(): void {
        $id=$this->accept();$old=$this->transport->pop();$first=Redis::get($this->guard($id));
        Redis::del($this->guard($id));DB::table('reports')->where('id',$id)->update(['dispatch_after'=>now()]);
        app(Reports::class)->dispatch($id);$next=Redis::get($this->guard($id));$this->assertNotSame($first,$next);
        Http::fake(['*'=>Http::response(['checksum'=>'one-result'],200)]);$old->fire();
        $this->assertSame($next,Redis::get($this->guard($id)));
        $this->transport->pop()->fire();Http::assertSentCount(1);
        $this->assertNull(Redis::get($this->guard($id)));$this->assertSame(0,$this->transport->size());
        $this->assertEquals(1,DB::table('metric_samples')->where('series','lab_completed_total{traffic="normal"}')->value('value'));
    }
    public function test_preclaim_worker_loss_is_recovered_after_native_reservation_exhaustion(): void {
        $id=$this->accept();$abandoned=$this->transport->pop();
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'pending','attempts'=>0]);
        $this->assertNotNull(Redis::get($this->guard($id)));
        $this->travel(21)->seconds();$redelivered=$this->transport->pop();
        try { app('queue.worker')->process('redis',$redelivered,new \Illuminate\Queue\WorkerOptions(maxTries:1,timeout:10)); }
        catch (\Illuminate\Queue\MaxAttemptsExceededException $e) { /* Native transport rejection precedes handle. */ }
        $this->assertNull(Redis::get($this->guard($id)));
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'pending','attempts'=>0]);
        app(Reports::class)->reconcile();$this->finish();
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed','attempts'=>1]);
    }
    public function test_rolled_back_enqueue_does_not_create_payload_or_guard(): void {
        $id=(string)Str::uuid();$this->ids[]=$id;
        try { DB::transaction(function() use($id) { $this->transport->push(new \App\Jobs\ProcessReport($id));throw new \RuntimeException('synthetic rollback'); }); }
        catch (\RuntimeException $e) { $this->assertSame('synthetic rollback',$e->getMessage()); }
        $this->assertSame(0,$this->transport->size());$this->assertNull(Redis::get($this->guard($id)));
    }
}
