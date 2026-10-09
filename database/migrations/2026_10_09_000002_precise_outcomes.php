<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
return new class extends Migration {
    public function up(): void {
        foreach (['accepted_at','deadline_at','completed_at'] as $column) DB::statement("ALTER TABLE reports ALTER COLUMN {$column} TYPE timestamp(6) with time zone");
    }
    public function down(): void {
        // Preserve precision when rolling back; downgrading timestamps discards evidence.
    }
};
