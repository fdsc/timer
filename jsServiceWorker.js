// Виноградов С.В. https://github.com/fdsc/timer
// chrome://inspect/#service-workers
// about:debugging

// https://developer.mozilla.org/ru/docs/Web/API/Service_Worker_API/Using_Service_Workers
// https://developer.mozilla.org/en-US/docs/Web/API/Cache

const version = 'Fgvh2yOexbi8';

self.addEventListener
(
	'install',
	function(event)
	{
		// Событие будет считаться незавершённым, пока воркер успешно не проинициализируется
		event.waitUntil
		(
			caches.open(version)
			.then
			(/*
				function(cache)
				{
					return cache.addAll
					([
						'index.html',
						'jsTimer.js',
						'B4v45ZrQwRVM.css'
					]);
				}*/
			)
		);
	}
);

self.addEventListener
(
	'fetch',
	function(event)
	{
		// Загружаем из сети
		var request = fetch(event.request)
		.then
		(
			function (response)
			{
				let responseClone = response.clone();

				// Кешируем заново
				caches.open(version)
				.then
				(
					function (cache)
					{
						console.debug("TimerJS: cache.put " + event.request.url);
						cache.put(event.request, responseClone);
					}
				);

				console.debug("TimerJS: service worker load from internet for url " + event.request.url);

				return response;
			}
		)
		.catch
		(
			function(error)
			{
				console.log("TimerJS: service worker load from the cache for url " + event.request.url);
				console.log(error);

				// Возвращаем запрошенный ресурс из кеша
				return caches.match(event.request)
				.then
				(
					function(response)
					{
						if (response !== undefined)
						{
							return response.clone();
						}
						else
						{
							// return caches.match('error.png');
							// https://developer.mozilla.org/en-US/docs/Web/API/Response
							var r = new Response
							(
								'Network is unreilable or error occured (TimerJS)',
								{
									// https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
									// Request Timeout
									"status" : 408,
									"statusText": "Network is unreilable or error occured (TimerJS)"
								}
							);

							console.error("TimerJS: service worker: network is unreilable or error occured");
							return r;
						}
					}
				);
			}
		);

		event.respondWith(request);
	}
);
