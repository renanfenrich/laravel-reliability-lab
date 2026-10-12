<?php
return ['default'=>env('QUEUE_CONNECTION','redis'),'connections'=>['redis'=>['driver'=>'report-redis','connection'=>'default','queue'=>'reports','retry_after'=>20,'block_for'=>1,'after_commit'=>true]],'failed'=>['driver'=>'null']];
