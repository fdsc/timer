var AC = null;
var audioSource = null;
var audio = null;
var gainNode = null;
var wave, osc, wavetable;
var soundRegime = 0;
var soundSwither;

var timerStorageNameConst = 'timers.';
var timerStorageName      = timerStorageNameConst;
var timersName = "";

var timersObject = 
{
	timers: [],
	saved:  []
};

function addTimer(id, milliSeconds, text, isEnd, fromSave)
{
	var now = new Date();
	var end = new Date(now.getTime() + milliSeconds).getTime();
	if (isEnd === true)
		end = milliSeconds;

	if (!text)
		text = "Таймер " + new Date(end).toLocaleString();

	timersObject.timers.push
	(
		{
			end:  end,
			endL: end,
			id:   id,
			text: text
		}
	);

	document.getElementById("text").value = "";

	if (!fromSave)
	{
		saveTimers();
		drawTimers();
	}

	playNull();
};

function saveTimers()
{
	localStorage.setItem(timerStorageName, JSON.stringify(timersObject));
};

function deleteTimer(MouseEvent)
{
	//console.error(this);
	//console.error(arguments);
	var main  = document.getElementById("main");
	var toDel = document.getElementById('timer-' + this.tid);

	var timers = timersObject.timers;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			timers.splice(curI, 1);

			saveTimers();
			main.removeChild(toDel);
			break;
		}
	}


	// hideAlert нельзя делать, т.к. вызов удаления таймера может быть из push-уведомления
	// hideAlert();
}

function deleteSavedTimer(MouseEvent)
{
	//console.error(this);
	//console.error(arguments);
	var main  = document.getElementById("timersShort");
	var toDel = document.getElementById('savedtimer-' + this.tid);

	var timers = timersObject.saved;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			timers.splice(curI, 1);

			saveTimers();
			main.removeChild(toDel);
			break;
		}
	}

	hideAlert();
}

function addTimer_Mil(milliSeconds)
{
	var te = document.getElementById("text");
	var text = te.value;
	te.value = '';

	var id = getNewId(timersObject.timers);
	addTimer(id, milliSeconds, text);

	hideAlert();
};

function addTimer0()
{/*
	Img[0]   = parseFloat(document.getElementById("Img1").value);*/
	
	// Аналогичный код внизу
	var h = parseFloat(document.getElementById("hours")  .value || 0);
	var m = parseFloat(document.getElementById("minutes").value || 0);
	var s = parseFloat(document.getElementById("seconds").value || 0);
	
	document.getElementById("hours")  .value = '';
	document.getElementById("minutes").value = '';
	document.getElementById("seconds").value = '';

	addTimer_Mil((h*3600 + m*60 + s)*1000);
};

function addTimer01()
{
	addTimer_Mil(1*60*1000);
};

function addTimer05()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(5*60*1000);
};

function addTimer15()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(15*60*1000);
};

function addTimer1()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(60*60*1000);
};

function addTimer4()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(4*60*60*1000);
};

function addTimer8()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(8*60*60*1000);
};

function addTimer24()
{
	var text = document.getElementById("text").value;
	addTimer_Mil(24*60*60*1000);
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

var silentEndTime = 0;
function play(freq, time, volume)
{
	if (silentEndTime > new Date().getTime())
		return;

	if (!AC)
		onAudioLoad();

	if (!AC || soundRegime == 2)
		return;

	/*
	audioSource = AC.createMediaElementSource(audio);
	audioSource.connect(gainNode).connect(AC.destination);
*//*
	wave = AC.createPeriodicWave(wavetable.real, wavetable.imag);
	osc  = AC.createOscillator();
    //osc.setPeriodicWave(wave);
	osc.type = 'sine';
    osc.frequency.value = freq ? freq : 261.626;
    osc.connect(gainNode).connect(AC.destination);

	osc.start();
	osc.stop(AC.currentTime + 0.99);
*/
	// i * qw = 2PI
	// i*440*Math.PI*2/AC.sampleRate = Math.PI*2
	// i*440/AC.sampleRate = 1
	// i*440/AC.sampleRate = 1
	// i = AC.sampleRate / 440;

	freq     = freq ? freq : 261.626;
	var qw   = freq*Math.PI*2/AC.sampleRate;
	// Ячеек массива в одном периоде
	var T    = Math.PI*2 / qw;
	time     = time   ? time   : 1.0;
	volume   = volume ? volume : 1.0;
	var bufferSize = Math.round(Math.floor(AC.sampleRate/T*time)*T);

	var buffer = AC.createBuffer(1, bufferSize, AC.sampleRate);
	var data = buffer.getChannelData(0);
	for (var i = 0; i < bufferSize; i++)
	{
		data[i] = volume * Math.sin(i * qw);
	}

/*
	for (var i = 0; i < bufferSize; i++)
	{
		data[i] += Math.sin(i*2 * qw) / 4;
	}
*/
	var noise = AC.createBufferSource();
	noise.buffer = buffer;
	noise.connect(gainNode).connect(AC.destination);
	noise.start();
};

function onAudioLoad()
{
	AC = new AudioContext();

	if (AC == null)
		return null;

	var gainVal = localStorage.getItem('gainVal');
	gainVal = gainVal ? gainVal : 1.0;

	gainNode = AC.createGain();
	gainNode.gain.value = gainVal;

	var gv = document.getElementById("gainVal");
	gv.textContent = gainVal;
	gv = document.getElementById("volume");
	gv.value = gainVal;

	wavetable =
	{
		'real': [
					1.000000/*,
					-0.000000,
					-0.203569,
					0.500000,
					-0.401676,
					0.137128,
					-0.104117,
					0.115965,
					-0.004413,
					0.067884,
					-0.008880,
					0.079300,
					-0.038756,
					0.011882,
					-0.030883,
					0.027608,
					-0.013429,
					0.003930*/
				],
		'imag': [
					1.000000/*,
					0.147621,
					-0.000001,
					0.000007,
					-0.000010,
					0.000005,
					-0.000006,
					0.000009,
					-0.000000,
					0.000008,
					-0.000001,
					0.000014,
					-0.000008,
					0.000003,
					-0.000009,
					0.000009,
					-0.000005,
					0.000002*/
				]
	};

	// hideAlert();
	playNull();

	return !!AC;
};

function addNull(str)
{
	str = '' + str;

	if (str.length == 1)
		return '0' + str;

	return str;
}

function formatDate(date)
{
	var str = 	addNull(date.getUTCHours())
		+ ':' + addNull(date.getUTCMinutes())
		+ ':' + addNull(date.getUTCSeconds());

	var days = date.getTime() / (24*3600*1000);
	if (days >= 1.0)
	{
		days = Math.floor(days);
		str = days + " дн. " + str;
	}

	return str;
}

function interval()
{
	var now = new Date().getTime();
	var difMin  = 24*60*60*1000;
	var minText = 'Таймер';

	var btn = document.getElementById("silent");
	btn.value = "выкл. 1 минута";

	if (silentEndTime > now)
	{
		btn.value = "выключено " + addNull(new Date(silentEndTime - now).getUTCSeconds());
	}

	for (var cur of timersObject.timers)
	{
		var tid = cur.id;

		var tt = document.getElementById('timer-' + tid + '-t');
		var dif = cur.end - now;

		if (dif <= 0)
		{
			if (cur.stopped !== true)
			{
				cur.stopped = true;
				cur.played  = 0;
				cur.playedA = 0;
				try
				{
					var textElement = document.getElementById("text");
					if (!textElement.value)
						textElement.value = cur.text;
				}
				catch (e)
				{
					console.error(e);
				}

				MakeNotification(cur, cur.text);
			}

			tt.textContent = '00:00:00';

			var tm = document.getElementById('timer-' + tid + '-del');
			if (cur.color && cur.color > 0)
			{
				tm.style.backgroundColor = 'yellow';
				cur.color = -1;
			}
			else
			{
				tm.style.backgroundColor = 'red';
				cur.color = 1;
			}

			if (soundRegime == 1)
			{
				if (cur.played == 0 || cur.played == 2)
					play();
			}
			else
			if (cur.playedA > 7)
			{
				if (cur.played == 0 || cur.played == 2)
					play(cur.played == 0 ? 698.456 : 440);
			}
			else
			if (cur.played <= cur.playedA || (cur.played % 2) == 0 && cur.played <= cur.playedA+2)
			{
				if ((cur.played % 2) == 0)
					play();
				else
					play(cur.playedA > 4  ? 698.456 : 349.228);
			}

			cur.end = new Date(now + 1000).getTime();
			cur.played++;
			if (cur.played > 14)
			{
				cur.played = 0;
				cur.playedA++;
/*
				if (cur.playedA > 7)
					cur.end = new Date(now + 8000);*/
/*
				// После длительного игнорирования сигнала, делаем перерыв на минуту
				if (cur.playedA > 7)
					cur.end = new Date(now + 60*1000).getTime();*/
			}
		}

		var end = new Date(dif);

		// Иначе это уже остановленный таймер
		if (cur.stopped !== true)
		tt.textContent = formatDate(end);

		if (dif < difMin || cur.stopped && difMin > 0)
		{
			if (cur.stopped && dif > 0)
				dif = 0;

			difMin = dif;
			if (cur.stopped !== true)
				minText = tt.textContent;
			else
			{
				minText = (cur.color > 0 ? '! ' : '') + cur.text;
			}
		}
	}

	document.title = minText;
};

function onClickToTimer(Element, text)
{
	return function()
	{
		var textElement = document.getElementById("text");
		textElement.value = text;
	};
};

function onClickToSavedTimer(Element, timer, addImmideatly)
{
	return function(mouseEvent)
	{
		if (addImmideatly || mouseEvent.shiftKey)
		{
			var id = getNewId(timersObject.timers);
			addTimer(id, 1000*(timer.h*3600 + timer.m*60 + timer.s), timer.name);

			// Контекстное меню не должно появится
			mouseEvent.preventDefault();
			return true;
		}

		var textElement = document.getElementById("text");

		if (timer.name)
			textElement.value = timer.name;

		if (timer.h)
			document.getElementById("hours")  .value = timer.h || "";
		
		if (timer.m)
			document.getElementById("minutes").value = timer.m || "";

		if (timer.s)
			document.getElementById("seconds").value = timer.s || "";
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
	tt.id = 'timer-' + timer.id + "-t";

	var tend = document.createElement("span");
	tc.appendChild(tend);
	tend.id = 'timer-' + timer.id + "-end";
	tend.textContent = new Date(timer.end).toLocaleString();
	tend.style.marginLeft = '10%';

	var tdel = document.createElement("div");
	div.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Удалить";
	tdel.addEventListener('click', deleteTimer);
	tdel.style.marginBottom = '30px';
	tdel.style.marginTop = '15px';
	tdel.id = 'timer-' + timer.id + "-del";

	var hr = document.createElement("hr");
	div.appendChild(hr);
}

function drawTimers()
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
				addTimer(cur.id, cur.end, cur.text, true, true);
				drawTimer(cur);
			}
		}
		else
		{
			timersObject.timers = [];
		}
	}

	drawTimersShorts();
};

function hideAlert()
{
	document.getElementById("alert").style.display = 'none';
	playNull();
};

function playNull()
{
	play(440, 0.01, 0.01);
}

var SoundRegimeText = 
		[
			'Звук включён',
			'Два низких гудка',
			'Звук выключен'
		];

function getSoundRegimeText(soundRegime)
{
	return SoundRegimeText[soundRegime];
}

function MakeNotification(timer, header, text)
{
	try
	{
		// var notification = new Notification('To do list', { body: text, icon: img });
		var notification = new Notification
								(
									header,
									{
										body: 				text || 'Таймер активен',
										requireInteraction: true,
										vibrate: 			[300, 2500, 500]
									}
								);

		notification.addEventListener
		(
			'click',
			function(event)
			{
				notification.close();
				deleteTimer.apply
				(
					{
						tid: timer.id
					}
				);
			},
			false
		);
	}
	catch
	{}
}

// https://developer.mozilla.org/en-US/docs/Web/API/Notifications_API/Using_the_Notifications_API
function InitializeNotification()
{
	try
	{
		var timersFromStorage = localStorage.getItem(timerStorageName);
		if (typeof(timersFromStorage) != "undefined" && timersFromStorage)
		{
			var t = JSON.parse(timersFromStorage);
			if (t && timersFromStorage.notifications)
				timersObject.notifications = timersFromStorage.notifications;

			if (!timersObject.notifications)
				timersObject.notifications = {};
		}

		if (Notification.permission != 'granted')
		{
			Notification.requestPermission().then
			(
				function(result)
				{
					if (!timersObject.notifications)
						timersObject.notifications = {};

					timersObject.notifications.permission = result;	// 'granted', 'denied', 'default'
					saveTimers();
				}
			);
		}
	}
	catch
	{}
}

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
	btn = document.getElementById("addTimer01");
	btn.addEventListener('click', addTimer01);
	btn = document.getElementById("addTimer05");
	btn.addEventListener('click', addTimer05);
	btn = document.getElementById("addTimer15");
	btn.addEventListener('click', addTimer15);
	btn = document.getElementById("addTimer1");
	btn.addEventListener('click', addTimer1);
	btn = document.getElementById("addTimer4");
	btn.addEventListener('click', addTimer4);
	btn = document.getElementById("addTimer8");
	btn.addEventListener('click', addTimer8);
	btn = document.getElementById("addTimer24");
	btn.addEventListener('click', addTimer24);

	btn = document.getElementById("alert");
	btn.addEventListener('click', hideAlert);

	btn = document.getElementById("volume");
	btn.addEventListener
	(
		'input', 
		function()
		{
			if (gainNode)
			{
				var gv = document.getElementById("gainVal");
				gainNode.gain.value = this.value;
				gv.textContent = this.value;

				localStorage.setItem('gainVal', this.value);
			}
		}
	);

	btn = document.getElementById("gainVal");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			if (me.altKey)
				play(660);
			else
				play();
		}
	);

	soundRegime  = localStorage.getItem('soundRegime') || 0;
	soundSwither = document.getElementById("soundSwither");
	soundSwither.textContent = getSoundRegimeText(soundRegime);
	soundSwither.addEventListener
	(
		'click',
		function(me)
		{
			soundRegime++;
			if (soundRegime >= SoundRegimeText.length)
			{
				soundRegime = 0;
			}

			localStorage.setItem('soundRegime', soundRegime)
			soundSwither.textContent = getSoundRegimeText(soundRegime);
		}
	);

	var gainVal = localStorage.getItem('gainVal') || 1.0;

	var gv = document.getElementById("gainVal");
	gv.textContent = gainVal;
	gv = document.getElementById("volume");
	gv.value = gainVal;

	btn = document.getElementById("silent");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			if (silentEndTime > new Date().getTime())
				silentEndTime = 0
			else
				silentEndTime = new Date().getTime() + 60*1000;
		}
	);
	
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

	btn = document.getElementById("saveTimer");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			var h = parseFloat(document.getElementById("hours")  .value || 0);
			var m = parseFloat(document.getElementById("minutes").value || 0);
			var s = parseFloat(document.getElementById("seconds").value || 0);

			var timerName = document.getElementById("text").value;

			addSavedTimer(h, m, s, timerName);
			saveTimers();
			drawTimersShorts();
		}
	);

	// audio = document.getElementById("audio");

	drawTimers();
	InitializeNotification();

	setInterval
	(
		interval,
		100
	);
};

function addSavedTimer(h, m, s, timerName)
{
	if (!timersObject.saved)
		timersObject.saved = [];

	var seconds = h*3600 + m*60 + s;
	var newTimer =
		{
			h:  h,
			m:  m,
			s:  s,
			id: getNewId(timersObject.saved),

			totalSeconds: seconds,
			name:         timerName,
			timeVal:      formatDate(new Date(seconds*1000))
		};

	timersObject.saved.push(newTimer);

	return newTimer;
}

function drawSavedTimer(timer)
{
	var main = document.getElementById("timersShort");
	
	var div  = document.createElement("div");
	div.id   = 'savedtimer-' + timer.id;
	main.appendChild(div);

	var te   = document.createElement("div");
	div.appendChild(te);
	te.textContent = timer.name;
	te.addEventListener('click',       onClickToSavedTimer(te, timer, false));
	te.addEventListener('contextmenu', onClickToSavedTimer(te, timer, true ));
	// te.style.marginLeft = '5%';

	var tc = document.createElement("div");
	div.appendChild(tc);

	var tt = document.createElement("span");
	tc.appendChild(tt);
	tt.id = 'timer-' + timer.id + "-t";

	var tend = document.createElement("span");
	tc.appendChild(tend);
	tend.id = 'timer-' + timer.id + "-end";
	tend.textContent = formatDate(new Date(timer.totalSeconds*1000));
	//tend.style.marginLeft = '10%';

	var tdel = document.createElement("div");
	div.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Удалить";
	tdel.addEventListener('click', deleteSavedTimer);
	tdel.style.marginBottom = '30px';
	tdel.style.marginTop = '15px';
	tdel.id = 'timer-' + timer.id + "-del";

	var hr = document.createElement("hr");
	div.appendChild(hr);
}

function drawTimersShorts()
{
	var main = document.getElementById("timersShort");
	main.textContent = "";

	var timersFromStorage = localStorage.getItem(timerStorageName);
	if (typeof(timersFromStorage) != "undefined" && timersFromStorage)
	{
		var t = JSON.parse(timersFromStorage);
		if (t && t.saved)
		{
			t = t.saved;
			if (t)
			{
				for (var i = 0; i < t.length; i++)
				{
					for (var j = i + 1; j < t.length; j++)
					{
						if (t[i].totalSeconds > t[j].totalSeconds)
						{
							var ai = t[i];
							var aj = t[j];
							t[i] = aj;
							t[j] = ai;
						}
					}
				}

				timersObject.saved = [];
				for (var cur of t)
				{
					var newTimer = addSavedTimer(cur.h, cur.m, cur.s, cur.name);
					drawSavedTimer(newTimer);
				}
			}
		}
		else
		{
			timersObject.saved = [];
		}
	}
};
