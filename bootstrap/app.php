<?php
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(api: __DIR__.'/../routes/api.php', commands: __DIR__.'/../routes/console.php')
    ->withMiddleware(function (Middleware $m) { $m->append(\App\Http\Middleware\Observe::class); })
    ->withExceptions(function (Exceptions $e) { $e->shouldRenderJsonWhen(fn () => true); })
    ->create();
