<?php
namespace Tests\Feature;
use App\Jobs\ProcessReport;
use App\Services\Reports;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;
class ReportsTest extends TestCase {
    use DatabaseMigrations;
    private function submit(string $key='test-key',array $payload=[],string $traffic='normal') {
        return $this->withHeaders(['Authorization'=>'Bearer synthetic-test-only','Idempotency-Key'=>$key,'X-Lab-Traffic'=>$traffic])->postJson('/api/reports',array_merge(['subject'=>'synthetic-test'],$payload));
    }
    private function report(array $payload=[]): string { Queue::fake(); return $this->submit('key-'.uniqid(),$payload,$payload?'fault':'normal')->assertStatus(202)->json('id'); }
    public function test_auth_validation_and_fault_controls(): void {
        $this->postJson('/api/reports',[])->assertStatus(401);
        $this->submit('a',['subject'=>'personal-data'])->assertStatus(422);
        $this->submit('b',['latency_ms'=>4001],'fault')->assertStatus(422);
        $this->submit('c',['fail_attempts'=>1])->assertStatus(403);
        config(['lab.faults'=>false]); $this->submit('d',[],'fault')->assertStatus(403);
    }
    public function test_durable_idempotency_and_payload_conflict(): void {
        Queue::fake(); $id=$this->submit()->assertStatus(202)->json('id');
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'pending']);
        $this->submit()->assertOk()->assertJsonPath('id',$id);
        $this->submit('test-key',['subject'=>'synthetic-other'])->assertStatus(409);
        $this->assertDatabaseCount('reports',1); Queue::assertPushed(ProcessReport::class,1);
    }
    public function test_queue_outage_accepts_committed_record_and_reconciles(): void {
        Queue::shouldReceive('connection')->andThrow(new \RuntimeException('synthetic queue unavailable'));
        $id=$this->submit()->assertStatus(202)->json('id');
        $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'pending']);
        Queue::fake(); $this->travel(6)->seconds(); app(Reports::class)->reconcile(); Queue::assertPushed(ProcessReport::class,1);
    }
    public function test_crash_before_dispatch_is_recovered(): void {
        $id=$this->report(); Queue::fake(); DB::table('reports')->where('id',$id)->update(['dispatch_after'=>now()->subSecond()]);
        app(Reports::class)->reconcile(); Queue::assertPushed(ProcessReport::class,1);
    }
    public function test_duplicate_delivery_has_one_result_and_one_completion(): void {
        $id=$this->report(); Http::fake(['*'=>Http::response(['checksum'=>'synthetic'],200)]);
        (new ProcessReport($id))->handle(); (new ProcessReport($id))->handle();
        Http::assertSentCount(1); $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed','attempts'=>1]);
        $this->assertEquals(1,DB::table('metric_samples')->where('series','lab_completed_total{traffic="normal"}')->value('value'));
    }
    public function test_retry_exhaustion_is_visible_and_backoff_is_enforced(): void {
        $id=$this->report(['fail_attempts'=>3]); Http::fake(['*'=>Http::response([],503)]);
        for($i=0;$i<3;$i++) { (new ProcessReport($id))->handle(); (new ProcessReport($id))->handle(); $this->travel(9)->seconds(); }
        Http::assertSentCount(3); $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'failed','attempts'=>3]);
        $this->withToken('synthetic-test-only')->getJson('/api/reports/'.$id)->assertOk()->assertJsonPath('state','failed');
    }
    public function test_expired_worker_lease_recovers_and_stale_result_is_fenced(): void {
        $id=$this->report();
        DB::table('reports')->where('id',$id)->update(['state'=>'processing','attempts'=>1,'lease_token'=>\Illuminate\Support\Str::uuid(),'lease_until'=>now()->subSecond()]);
        app(Reports::class)->reconcile(); Http::fake(['*'=>Http::response(['checksum'=>'recovered'],200)]);
        (new ProcessReport($id))->handle(); $this->assertDatabaseHas('reports',['id'=>$id,'state'=>'completed','attempts'=>2]);
    }
    public function test_deadline_misses_include_unfinished_failed_and_late_completion(): void {
        $ids=[$this->report(),$this->report(),$this->report()];
        DB::table('reports')->whereIn('id',$ids)->update(['deadline_at'=>now()->subSecond()]);
        DB::table('reports')->where('id',$ids[1])->update(['state'=>'failed']);
        app(Reports::class)->deadlines(); Http::fake(['*'=>Http::response(['checksum'=>'late'],200)]);
        (new ProcessReport($ids[2]))->handle(); app(Reports::class)->deadlines();
        $this->assertEquals(3,DB::table('reports')->where('deadline_met',false)->count());
        $this->assertEquals(3,DB::table('metric_samples')->where('series','lab_deadlines_total{outcome="miss",traffic="normal"}')->value('value'));
    }
    public function test_deadline_success_is_counted_once(): void {
        $id=$this->report(); Http::fake(['*'=>Http::response(['checksum'=>'ok'],200)]); (new ProcessReport($id))->handle();
        $this->travel(61)->seconds(); app(Reports::class)->deadlines(); app(Reports::class)->deadlines();
        $this->assertDatabaseHas('reports',['id'=>$id,'deadline_met'=>true]);
        $this->assertEquals(1,DB::table('metric_samples')->where('series','lab_deadlines_total{outcome="met",traffic="normal"}')->value('value'));
    }
    public function test_subsecond_deadline_boundary_preserves_a_late_miss(): void {
        $id=$this->report(); $deadline=now()->subSeconds(2)->startOfSecond()->addMicroseconds(100000);
        DB::table('reports')->where('id',$id)->update(['state'=>'completed','deadline_at'=>$deadline->format('Y-m-d H:i:s.uP'),'completed_at'=>$deadline->copy()->addMicroseconds(100000)->format('Y-m-d H:i:s.uP')]);
        app(Reports::class)->deadlines(); $this->assertDatabaseHas('reports',['id'=>$id,'deadline_met'=>false]);
    }
    public function test_stale_attempt_cannot_overwrite_recovered_result(): void {
        $id=$this->report();
        $calls=0;
        Http::fake(function() use($id,&$calls) {
            if(++$calls>1) return Http::response(['checksum'=>'current-token'],200);
            DB::table('reports')->where('id',$id)->update(['lease_until'=>now()->subSecond()]);
            app(Reports::class)->reconcile();
            (new ProcessReport($id))->handle();
            return Http::response(['checksum'=>'stale-token'],200);
        });
        (new ProcessReport($id))->handle();
        $r=DB::table('reports')->where('id',$id)->first();
        $this->assertSame('current-token',json_decode($r->result,true)['checksum']);
        $this->assertEquals(2,$r->attempts);
        $this->assertEquals(1,DB::table('metric_samples')->where('series','lab_completed_total{traffic="normal"}')->value('value'));
    }
    public function test_buffered_json_has_correct_length_framing(): void {
        Queue::fake(); $response=$this->submit();
        $response->assertHeader('Content-Length',(string)strlen($response->getContent()));
    }
    public function test_liveness_and_readiness_have_distinct_semantics(): void {
        $this->getJson('/api/live')->assertOk();
        \Illuminate\Support\Facades\Redis::shouldReceive('ping')->andThrow(new \RuntimeException('synthetic redis outage'));
        $this->getJson('/api/ready')->assertStatus(503); $this->getJson('/api/live')->assertOk();
    }
}
