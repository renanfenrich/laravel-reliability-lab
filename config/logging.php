<?php
return ['default'=>'stderr','channels'=>['stderr'=>['driver'=>'monolog','handler'=>Monolog\Handler\StreamHandler::class,'with'=>['stream'=>'php://stderr'],'formatter'=>Monolog\Formatter\JsonFormatter::class,'level'=>'info']]];
