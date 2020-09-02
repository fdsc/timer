﻿var AC = null;
var audioSource = null;
var audio = null;
var gainNode = null;
var wave, osc, wavetable;
var soundRegime = 0;
var soundSwither;

var timerStorageNameConst = 'stopwatch.';
var timerStorageName      = timerStorageNameConst;
var timersName = "";

var timersObject = 
{
	timers: []
};

function addTimerObject(newTimer)
{
	timersObject.timers.push(newTimer);
}

function getNewTimeObject(stopped)
{
	return {
				start   : new Date().getTime(),
				stopped : stopped || false,
				all     : false
			};
}

function addTimer({id, times, text, stopped, fromSave})
{
	if (!times)
	{
		times = [];
		times.push(getNewTimeObject(stopped));
	}

	addTimerObject
	(
		{
			id:   	  id,
			text: 	  text,
			toDelete: false,
			stopped:  stopped || false,
			times:    times   || [],
			all:      0
		}
	);

	document.getElementById("text").value = "";

	if (!fromSave)
	{
		saveTimers();
		drawTimers();
	}
};

function timerToStop(cur)
{
	var stopElement = document.getElementById('timer-' + cur.id + "-stop");

	var time = cur.times[cur.times.length - 1];
	if (time.stopped !== false)	// Запускаем новый таймер
	{
		stopElement.textContent = "Стоп";
		cur.times.push(getNewTimeObject());
		cur.stopped  = false;
	}
	else	// Останавливаем старый таймер
	{
		stopElement.textContent = "Старт";
		time.stopped   = Date.now();
		time.all       = time.stopped - time.start;
		time.allToText = formatDate(new Date(time.all));

		cur.stopped    = true;
		cur.all        = AllTimesCalculate(cur);
		cur.allToText  = formatDate(new Date(cur.all));

		time.allForAll = cur.all;
	}
}

function stopTimer()
{
	var stopElement = document.getElementById('timer-' + this.tid + "-stop");

	var timers = timersObject.timers;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			timerToStop(cur);
			break;
		}
	}

	saveTimers();
	drawTimers();
}

function markTimer()
{
	var stopElement = document.getElementById('timer-' + this.tid + "-reper");

	var timers = timersObject.timers;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			var time      = cur.times[cur.times.length - 1];
			var newTime   = getNewTimeObject();
			if (time.stopped === false)
			{
				time.stopped  = Date.now();
				time.all      = time.stopped - time.start;

				newTime.start = time.stopped;
			}
			else
			{
			}

			cur.times.push(newTime);

			break;
		}
	}

	saveTimers();
	drawTimers();
}

function deleteTimer(MouseEvent)
{
	//console.error(this);
	//console.error(arguments);
	// var main  = document.getElementById("main");
	var toDel = document.getElementById('timer-' + this.tid);

	var timers = timersObject.timers;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			if (!isTimerToDelete(cur))
			{
				timers[curI].toDelete = new Date().getTime();

				return;
			}

			if (new Date() - cur.toDelete <= 350)
				return;

			timers.splice(curI, 1);

			saveTimers();
			// main.removeChild(toDel);
			toDel.parentNode.removeChild(toDel);

			// Вызов для того, чтобы можно было предупредить пользователя о том,
			// что он удалил задачу, которая есть в контрольном списке
			// drawTimersShorts();
			break;
		}
	}


	// hideAlert нельзя делать, т.к. вызов удаления таймера может быть из push-уведомления
	// hideAlert();
}

function addTimer0()
{
	var te   = document.getElementById("text");
	var text = te.value;
	te.value = '';

	var id = getNewId(timersObject.timers);
	addTimer({id: id, text: text});
};

var ID = 1;
function getNewId(timers)
{
	var id = ID;
	for (var cur of timers)
	{
		if (cur.id >= id)
			id = cur.id + 1;
	}

	ID = id + 1;
	return id;
};

function loadSoundRegime()
{
	try
	{
		var soundRegime = localStorage.getItem(timerStorageName + '.soundRegime');
		if (typeof(soundRegime) != "undefined" && soundRegime)
		{
			soundRegimeObject = JSON.parse(soundRegime);
		}
	}
	catch (e)
	{
		console.error(e);
	}
}

function addNull(str)
{
	str = '' + str;

	if (str.length == 1)
		return '0' + str;

	return str;
}

function formatDate(date)
{
	var str =   addNull(date.getUTCMinutes())
		+ ':' + addNull(date.getUTCSeconds())
		+ '.' + addNull(date.getUTCMilliseconds());

	if (date.getUTCHours() >= 1.0)
	{
		str = addNull(date.getUTCHours()) + "ч. " + str;
	}

	var days = date.getTime() / (24*3600*1000);
	if (days >= 1.0)
	{
		days = Math.floor(days);
		str = days + " дн. " + str;
	}

	return str;
}

function formatDateMinimal(date)
{
	var h = date.getUTCHours();
	var m = date.getUTCMinutes();
	var s = date.getUTCSeconds();
	var str = '';

	if (h > 0 || m > 0 || s > 0)
	{
		str = addNull(s);
	}
	else
	if (days == 0)
	{
		str = addNull(s);
	}

	if (h > 0 || m > 0)
	{
		str = addNull(m) + ":" + str;
	}

	if (h > 0)
	{
		str = addNull(h) + ":" + str;
	}

	var days = date.getTime() / (24*3600*1000);
	if (days >= 1.0)
	{
		days = Math.floor(days);
		str = days + " дн. " + str;
	}

	return str;
}

function AllTimesCalculate(timer, lastIndex = -1)
{
	if (lastIndex < 0)
		lastIndex = timer.times.length - 1;

	var now   = Date.now();
	var all   = 0;
	for (var i = 0; i <= lastIndex; i++)
	{
		var time = timer.times[i];
		if (time.stopped)
		{
			all += time.all;
		}
		else
		{
			all += now - time.start;
		}
	}

	return all;
}

var lastDateOfPlay = false;
function interval()
{
	var now = new Date().getTime();
	var difMin  = 24*60*60*1000;

	var isPlay = false;
	for (let cur of timersObject.timers)
	{
		var tid = cur.id;

		let tt  = document.getElementById('timer-' + tid + '-t');

		if (cur.stopped)
		{
		}
		else
		{
			setTimeout
			(
				function()
				{
					cur.all        = AllTimesCalculate(cur);
					cur.allToText  = formatDate(new Date(cur.all));
					tt.textContent = cur.allToText;

					var time       = cur.times[cur.times.length - 1];

					time.allForAll = cur.all;
				},
				0
			);
		}

		if (cur.toDelete !== false)
		if (isTimerToDelete(cur))
		{
			var tdel = document.getElementById('timer-' + tid + '-del');
			tdel.textContent = "Точно удалить?";
		}
		else
		{
			if (cur.toDelete)
			{
				var tdel = document.getElementById('timer-' + tid + '-del');
				tdel.textContent = "Удалить";
			}

			cur.toDelete = false;
		}
	}
};

function onClickToTimer(Element, text)
{
	return function()
	{
		var textElement = document.getElementById("text");
		textElement.value = text;

		hideAlert();
	};
};

function drawTimer(timer)
{
	var main = document.getElementById("main");

	var div  = document.createElement("div");
	div.id   = 'timer-' + timer.id;
	main.appendChild(div);

	var te   = document.createElement("div");
	div.appendChild(te);
	te.textContent = timer.text;
	te.addEventListener('click', onClickToTimer(te, timer.text));
	// te.style.marginLeft = '5%';

	var tc = document.createElement("div");
	div.appendChild(tc);

	var tt = document.createElement("span");
	tc.appendChild(tt);
	tt.textContent = timer.allToText; //formatDate(new Date(timer.all));
	tt.id = 'timer-' + timer.id + "-t";
/*
	var tend = document.createElement("span");
	tc.appendChild(tend);
	tend.id = 'timer-' + timer.id + "-end";
	tend.textContent = new Date(timer.endL).toLocaleString();
	tend.style.marginLeft = '10%';
*/
	var tdeldiv = document.createElement("div");
	div.appendChild(tdeldiv);
	tdeldiv.id = 'timer-' + timer.id + "-deldiv";
	tdeldiv.style.marginBottom = '30px';
	tdeldiv.style.marginTop = '15px';

	var tb = document.createElement("table");
	tdeldiv.appendChild(tb);
	tb.style.width = "100%";

	for (var i = 0; i < timer.times.length; i++)
	{
		var time = timer.times[i];
		if (!time.stopped)
			break;

		var etime = document.createElement("tr");
		etime.id = 'timer-' + timer.id + "-time-" + i;
		tb.appendChild(etime);

		var stopTime = time.stopped || Date.now();

		var tm = document.createElement("td");
		tm.textContent = formatDate(new Date(stopTime - time.start));
		etime.appendChild(tm);
		tm.style.marginLeft = '5%';

		tm = document.createElement("td");
		tm.textContent = formatDate(new Date(time.allForAll));
		etime.appendChild(tm);
		tm.style.marginLeft = '5%';

		tm = document.createElement("td");
		tm.textContent = new Date(time.start).toLocaleString();
		etime.appendChild(tm);
		tm.style.marginLeft = '10%';
		tm.style.paddingLeft = '10%';

		tm = document.createElement("td");
		tm.textContent = new Date(time.stopped).toLocaleString();
		etime.appendChild(tm);
		tm.style.marginLeft = '5%';
	}

	var tdel = document.createElement("span");
	tdeldiv.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Стоп";
	tdel.addEventListener('click', stopTimer);
	tdel.id = 'timer-' + timer.id + "-stop";

	if (timer.stopped)
	{
		tdel.textContent = "Старт";
	}
	else
	{
	}

	tdel = document.createElement("span");
	tdeldiv.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Репер";
	tdel.addEventListener('click', markTimer);
	tdel.id = 'timer-' + timer.id + "-reper";
	tdel.style.marginLeft = '10%';

	tdel = document.createElement("span");
	tdeldiv.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Удалить";
	tdel.addEventListener('click', deleteTimer);
	tdel.id = 'timer-' + timer.id + "-del";
	tdel.style.marginLeft = '10%';
	
	if (isTimerToDelete(timer))
	{
		tdel.textContent = "Точно удалить?";
	}
	else
	{
		timer.toDelete = false;
	}

	var hr = document.createElement("hr");
	div.appendChild(hr);
}

var timerToDeleteInterval = 10*1000;
function isTimerToDelete(timer)
{
	if (!timer.toDelete)
		return false;

	return new Date().getTime() - timer.toDelete <= timerToDeleteInterval;
}

function saveTimers()
{
	localStorage.setItem(timerStorageName, JSON.stringify(timersObject));
};

function MergeTimers(text)
{
	var success = true;
	try
	{
		if (typeof(text) == "undefined" || !text)
		{
			return false;
		}

		var t = JSON.parse(text);
		if (!t || !t.timers || !t.saved)
			return false;

		for (var cur of t.timers)
		{
			try
			{
				var found = false;
				for (var s of timersObject.timers)
				{
					if (s.name == cur.name && s.end == cur.end)
					{
						found = true;
						break;
					}
				}

				if (!found)
					addTimer({id: getNewId(timersObject.timers), times: cur.times, text: cur.text, stopped: true, fromSave: true});
			}
			catch (e)
			{
				success = false;
				console.error(e);
			}
		}
	}
	catch (e)
	{
		console.error(e);
		return false;
	}

	saveTimers();
	drawTimers();

	return success;
}

function drawTimersGeneral()
{
	var main = document.getElementById("main");
	main.textContent = "";

	var timersFromStorage = localStorage.getItem(timerStorageName);
	if (typeof(timersFromStorage) != "undefined" && timersFromStorage)
	{
		var t = JSON.parse(timersFromStorage);
		if (t && t.timers)
		{
			t = t.timers;
			for (var i = 0; i < t.length; i++)
			{
				for (var j = i + 1; j < t.length; j++)
				{
					if (t[i].end > t[j].end)
					{
						var ai = t[i];
						var aj = t[j];
						t[i] = aj;
						t[j] = ai;
					}
				}
			}

			timersObject.timers = [];
			for (var cur of t)
			{
				addTimerObject(cur);
				drawTimer(cur);
			}
		}
		else
		{
			timersObject.timers = [];
		}
	}
}

function drawTimers()
{
	try
	{
		drawTimersGeneral();
	}
	catch (e)
	{
		console.error(e);
	}

	// drawTimersShorts();
};
/*
function hideAlert()
{
	document.getElementById("alert").style.display = 'none';
	playNull();
};
*/
// Эта функция работает быстрее, поэтому нет проблем с тем, что таймер может не реагировать при его перерисовке
/*
function updateDeleteTextForTimersShorts()
{
	lastToDeleteSavedTimer = false;	// см. drawTimersShorts
	for (var cur of timersObject.saved)
	{
		var te = document.getElementById('timer-' + cur.id + "-del");
		if (isTimerToDelete(cur))
		{
			if (cur.isInterval)
			{
				te.value = "Удалить?";
			}
			else
			{
				te.textContent = "Точно удалить?";
			}
		}
		else
		{
			cur.toDelete = false;

			if (cur.isInterval)
			{
				te.value = "X";
			}
			else
			{
				te.textContent = "Удалить";
			}
		}

		// Устанавливаем необходимость перерисовки таймеров, если это необходимо
		if (cur.toDelete)
			lastToDeleteSavedTimer = cur.toDelete;

	}
}
*/
window.onload = function()
{
	if (document.location.search)
	{
		var s = document.location.search.match(/name=(.*)/);
		if (s.length == 2)
		{
			timersName = s[1];
			if (timersName)
			{
				timerStorageName = timerStorageNameConst + timersName;

				var timersNameElement = document.getElementById("timersName");
				timersNameElement.textContent = "Имя хранилища таймеров: " + timersName;
			}
		}
	}

	var btn = document.getElementById("addTimer");
	btn.addEventListener('click', addTimer0);

	btn = document.getElementById("resetText");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			var timerNameElement = document.getElementById("text");
			timerNameElement.value = '';
		}
	);
/*
	btn = document.getElementById("SaveToClipboard");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			navigator.clipboard.writeText(JSON.stringify(timersObject))
			.then
			(
				function()
				{
					// alert("Таймеры сохранены в буфер обмена");
				}
			)
			.catch
			(
				function(e)
				{
					alert("Не удалось сохранить таймеры в буфер обмена");
					console.error(e);
				}
			);
		}
	);

	btn = document.getElementById("LoadFromClipboard");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			navigator.clipboard.readText()
			.then
			(
				function(text)
				{
					if (!MergeTimers(text))
					{
						alert("Кажется, формат копии таймеров не верен. Убедитесь, что вы загрузили резервную копию таймеров в буфер обмена из текстового файла");
					}
				}
			)
			.catch
			(
				function(e)
				{
					alert("Не удалось загрузить таймеры из буфера обмена");
					console.error(e);
				}
			);
		}
	);
*/
	// audio = document.getElementById("audio");

	drawTimers();
// 	InitializeNotification();

	setInterval
	(
		interval,
		33
	);
};


// https://developer.mozilla.org/ru/docs/Web/API/Service_Worker_API/Using_Service_Workers
if ('serviceWorker' in navigator)
{
	navigator.serviceWorker.register
	(
		document.location.pathname + 'jsServiceWorker.js',
		{ scope: document.location.pathname }	// Область регистрации ServiceWorker
	)
	.then
	(
		function(reg)
		{

			if (reg.installing)
			{
				console.log('Service worker installing');
			}
			else
			if (reg.waiting)
			{
				console.log('Service worker installed');
			}
			else
			if (reg.active)
			{
				console.log('Service worker active');
			}

		}
	)
	.catch
	(
		function(error)
		{
			console.error('ServiceWorker registration failed with ' + error);
		}
	);
}
else
{
	console.error('ServiceWorker support not found in your browser');
}
