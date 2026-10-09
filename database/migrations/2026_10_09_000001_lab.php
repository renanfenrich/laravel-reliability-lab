<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;
return new class extends Migration {
    public function up(): void {
        Schema::create('reports',function(Blueprint $t) {
            $t->uuid('id')->primary(); $t->string('idempotency_key',128)->unique();
            $t->string('request_id',64); $t->string('payload_hash',64); $t->jsonb('payload');
            $t->string('traffic',10); $t->string('state',16)->default('pending');
            $t->unsignedInteger('attempts')->default(0); $t->uuid('lease_token')->nullable();
            $t->timestampTz('lease_until')->nullable(); $t->timestampTz('dispatch_after')->index(); $t->timestampTz('available_at');
            $t->timestampTz('accepted_at'); $t->timestampTz('deadline_at')->index();
            $t->timestampTz('completed_at')->nullable(); $t->boolean('deadline_met')->nullable();
            $t->jsonb('result')->nullable(); $t->string('error')->nullable();
        });
        DB::statement("ALTER TABLE reports ADD CONSTRAINT report_state CHECK (state IN ('pending','processing','completed','failed'))");
        Schema::create('metric_samples',function(Blueprint $t) { $t->string('series',240)->primary(); $t->double('value')->default(0); });
    }
    public function down(): void { Schema::dropIfExists('metric_samples'); Schema::dropIfExists('reports'); }
};
