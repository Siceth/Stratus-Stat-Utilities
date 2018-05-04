<?php

// START CONFIG

$cacheDir = '../path/to/cache';
$cacheDays = 2;

// END CONFIG

header('Content-type: text/plain');
if(isset($_GET['request'])) {
	$_GET['request'] = strtolower($_GET['request']);
	if(!isset($_GET['force-renew']) && (time()-(file_exists($cacheDir.$_GET['request']) ? filemtime($cacheDir.$_GET['request']) : 0)) < $cacheDays*86400) {
		echo file_get_contents($cacheDir.$_GET['request']);
	} else {
		$response = substr(get_headers('https://stratus.network/'.$_GET['request'])[0], 9, 3);
		if($response < 400) {
			ob_start();
			echo "<!-- Cached ".date('Y-m-d h:i:s')." EST -->\n";
			$start = microtime(1);
			echo file_get_contents('https://stratus.network/'.$_GET['request']).'<!-- Page took '.(microtime(1)-$start).'s to load from Stratus -->';
			$ob = ob_get_contents();
			if(!ob_end_flush() || !file_put_contents($cacheDir.$_GET['request'], $ob)) {
				http_response_code(500);
				echo '[*] Server cache failed!';
			}
		} else {
			http_response_code($response);
			echo 'Error '.$response;
		}
	}
} else {
	echo "Stratus Network Website Cache/Mirror\n====================================\n\nUsage: /<request>[?force-renew]\n\n- Requests take from https://stratus.network/<request>, GET omitted\n- Results are cached for ".$cacheDays." days\n- Cache is overriden with the force-renew parameter\n- Errors are forwarded (overridden by cache)";
}
?>