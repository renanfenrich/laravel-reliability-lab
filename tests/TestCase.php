<?php
namespace Tests;
abstract class TestCase extends \Illuminate\Foundation\Testing\TestCase {
    public function createApplication() {
        $app=parent::createApplication();
        $app['config']->set('database.connections.pgsql.database','lab_test');
        $app['config']->set('lab.token','synthetic-test-only');
        $app['config']->set('lab.faults',true);
        return $app;
    }
}
