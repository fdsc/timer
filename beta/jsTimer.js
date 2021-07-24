﻿var AC = null;
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

var soundRegimeObject = 
{
	gainVal:     1.0,
	soundRegime: 0,
	DeferTime:   1
};

var SoundRegimeText = 
		[
			'Звук включён',
			'Два низких гудка',
			'Два низких гудка: чистый тон',
			'Два гудка на каждый таймер',
			'Звук отключён'
		];

var SoundDisableRegime = SoundRegimeText.length - 1;

var notificationObjects = {};

function addTimerObject(newTimer)
{
	timersObject.timers.push(newTimer);
}

function addTimer(id, milliSeconds, text, isEnd, fromSave)
{
	var now = new Date();
	var end = new Date(now.getTime() + milliSeconds).getTime();
	if (isEnd === true)
		end = milliSeconds;

	if (!text)
		text = "Таймер " + new Date(end).toLocaleString();

	addTimerObject
	(
		{
			end:  	       end,
			// end изменяется, когда таймеру нужно помигать. endL - не изменяется никогда (если только таймер не отложен)
			endL: 	       end,
			endS:          end,	// Не изменяется вообще никогда
			id:   	       id,
			text: 	       text,
			toDelete:      false,
			isControlTask: false,
			deferred:      false,
			Important:     false
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

function importantTimer(MouseEvent)
{
	var timers = timersObject.timers;
	for (var curI = 0; curI < timers.length; curI++)
	{
		var cur = timers[curI];
		if (cur.id == this.tid)
		{
			cur.Important = !cur.Important;
			saveTimers();
			drawTimers();

			return;
		}
	}
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
			if (!cur.stopped && !isTimerToDelete(cur))
			{
				timers[curI].toDelete = new Date().getTime();

				return;
			}

			if (new Date() - cur.toDelete <= 350)
				return;

			timers.splice(curI, 1);

			try
			{
				var notification = notificationObjects[cur.id];
				if (notification instanceof Notification)
				{
					notification.close();
					delete notificationObjects[cur.id];
				}
			}
			catch (e)
			{
				console.error(e);
			}

			saveTimers();
			// main.removeChild(toDel);
			toDel.parentNode.removeChild(toDel);

			// Вызов для того, чтобы можно было предупредить пользователя о том,
			// что он удалил задачу, которая есть в контрольном списке
			drawTimersShorts();
			break;
		}
	}


	// hideAlert нельзя делать, т.к. вызов удаления таймера может быть из push-уведомления
	// hideAlert();
}

var lastToDeleteSavedTimer = false;
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
			if (!isTimerToDelete(cur))
			{
				cur.toDelete = new Date().getTime();
				lastToDeleteSavedTimer = cur.toDelete;
 
				// Нужно сохранить, т.к. drawTimersShorts восстанавливает данные из сохранения
				/*saveTimers();
				drawTimersShorts();*/
				updateDeleteTextForTimersShorts();
				hideAlert();
				return;
			}

			if (new Date() - cur.toDelete <= 500)
				return;

			timers.splice(curI, 1);

			saveTimers();
			// main.removeChild(toDel);
			drawTimersShorts();

			break;
		}
	}

	hideAlert();
}

function addControlTask()
{
	var h = parseFloat(document.getElementById("hours")  .value || 0);
	var m = parseFloat(document.getElementById("minutes").value || 0);
	var s = parseFloat(document.getElementById("seconds").value || 0);

	var te = document.getElementById("text");
	var text = te.value;
	te.value = '';

	// addSavedTimer(id, h, m, s, timerName, savedInterval, toDelete, isControlTask)
	addSavedTimer(0, h, m, s, text, false, false, true);

	hideAlert();

	saveTimers();
	drawTimers();
}

function addTimer_Mil(milliSeconds)
{
	var te = document.getElementById("text");
	var text = te.value;
	te.value = '';

	var id = getNewId();
	addTimer(id, milliSeconds, text);

	hideAlert();
};

var daysOfWeek = [['по', 'пн'], ['вт'], ['ср'], ['чт', 'че'], ['пя', 'пт'], ['сб', 'су'], ['вс', 'во']];
function addTimer0()
{/*
	Img[0]   = parseFloat(document.getElementById("Img1").value);*/

	var addAbsDate = document.getElementById("addAbsDate");

	if (addAbsDate.checked)
	{
		var now = new Date();

		var h = parseInt(document.getElementById("hours").value || now.getFullYear());
		var m = document.getElementById("minutes").value;
		var s = document.getElementById("seconds").value;

		// На всякий случай, исправляем ошибки, типа 12,00. Исправляется только первое вхождение
		s = s.replace(/[^0-9]/, ":");		// Первый неправильный символ в двоеточие
		s = s.replaceAll(/[^0-9\:]/g, "");	// Все оставшиеся символы удаляем
		s = s.replaceAll(/\:+/g, ":");		// Множественные повторения двоеточий - в одно двоеточие

		var [day, month]     = m.split(".");
		var [hours, minutes] = s.split(":");

		if (!hours && parseInt(hours) != "0")
			hours = now.getHours();
		if (!minutes && parseInt(minutes) != "0")
			minutes = now.getMinutes();

		if (!month)
		{
			month = now.getMonth() + 1;
		}
		else
		if (isNaN(parseInt(month)))
		{
			if (month.startsWith("я"))
			{
				month = 1;
			}
			else
			if (month.startsWith("ф"))
			{
				month = 2;
			}
			else
			if (month.startsWith("мар") || month.startsWith("мат") || month.startsWith("мап"))	// мат - ошибка при написании марта
			{
				month = 3;
			}
			else
			if (month.startsWith("ап"))
			{
				month = 4;
			}
			else
			if (month.startsWith("май") || month.startsWith("мая"))
			{
				month = 5;
			}
			else
			if (month.startsWith("июн"))
			{
				month = 6;
			}
			else
			if (month.startsWith("июл"))
			{
				month = 7;
			}
			else
			if (month.startsWith("ав"))
			{
				month = 8;
			}
			else
			if (month.startsWith("с"))
			{
				month = 9;
			}
			else
			if (month.startsWith("о"))
			{
				month = 10;
			}
			else
			if (month.startsWith("н"))
			{
				month = 11;
			}
			else
			if (month.startsWith("д"))
			{
				month = 12;
			}
		}

		var dtp = null;
		if (!day)
		{
			day = now.getDate();
		}
		else
		if (day.trim && day.trim().startsWith("+"))
		{
			var str = day.trim();
			var N = 0;
			if (str == "+")
				N = 1;
			else
			if (str == "++")
				N = 2;
			else
			if (str == "+++")
				N = 3;
			else
			if (str == "++++")
				N = 4;
			else
			{
				str = str.substr(1);	// Убираем "+"
				N   = parseInt(str);
				if (isNaN(N))
					N = 0;
			}

			var afterDay = new Date(now.getTime() + N * 1000*3600*24);
			day = afterDay.getDate();

			month = afterDay.getMonth() + 1;
			h     = afterDay.getFullYear();
		}
		else
		// Если мы хотим, чтобы можно было ввести "пятница" и т.п.
		if (day.trim && isNaN(parseInt(day.trim())))
		{
			day = day.trim();
			var selectedDayOfWeek = now.getDay();

			breakDayLabel:
			for (var i = 0; i < daysOfWeek.length; i++)
			{
				var dayNameStarts = daysOfWeek[i];
				for (var j = 0; j < daysOfWeek.length; j++)
				{
					if (day.startsWith(dayNameStarts[j]))
					{
						// i - это день недели, начиная с 0, j - это представление этого дня недели
						// Т.к. день недели, начиная с нуля, то мы прибавляем к нему 1
						// Потому что getDay() даёт числа, начиная с 0, но воскресенье - это 0
						selectedDayOfWeek = i + 1;
						if (selectedDayOfWeek >= 7)
							selectedDayOfWeek = 0;

						break breakDayLabel;
					}
				}
			}

			// Первое число, т.к. чтобы сработало "пят.октября"
			// нужно начинать сразу с первого числа этого месяца, а не с текущего
			var tmpDay = 1; // now.getDate()
			dtp = Date.parse(h + "." + month + "." + tmpDay + " " + hours + ":" + minutes);
			if (isNaN(dtp))
				dtp = Date.parse(h + "-" + month + "-" + tmpDay + " " + hours + ":" + minutes);

			dtp = new Date(dtp);
			var cntForError = 368;

			while (dtp.getDay() != selectedDayOfWeek || dtp.getTime() < now.getTime())
			{
				dtp = new Date(dtp.getTime() + 24*3600*1000);
				cntForError--;
				if (cntForError < 0)
				{
					dtp = null;
					break;
				}
			}
		}

		if (dtp == null || isNaN(dtp))
			dtp  = Date.parse(h + "." + month + "." + day + " " + hours + ":" + minutes);

		if (isNaN(dtp))
			dtp = Date.parse(h + "-" + month + "-" + day + " " + hours + ":" + minutes);

		var future = new Date(dtp).getTime();

		var mil = future - now.getTime();
		// Производим проверку, что это уже не на сегодня, а на завтра
		// Год не проверяем, т.к. он уже заполнен, да и неважно,
		// т.к. если год другой - то одни сутки не помогут
		if (mil < 0 && !m)
		{
			mil += 1000*3600*24;
		}

		addTimer_Mil(mil);

		addAbsDate.checked = false;
		addAbsDateClicked();
	}
	else
	{
		// Аналогичный код внизу в нескольких местах для сохранённых таймеров
		var h = parseFloat(document.getElementById("hours")  .value || 0);
		var m = parseFloat(document.getElementById("minutes").value || 0);
		var s = parseFloat(document.getElementById("seconds").value || 0);

		addTimer_Mil((h*3600 + m*60 + s)*1000);
	}

	document.getElementById("hours")  .value = '';
	document.getElementById("minutes").value = '';
	document.getElementById("seconds").value = '';
};

function addAbsDateClicked()
{
	var addAbsDate      = document.getElementById("addAbsDate");
	var addAbsDateLabel = document.getElementById("addAbsDateLabel");

	var h = document.getElementById("hours")  ;
	var m = document.getElementById("minutes");
	var s = document.getElementById("seconds");

	if (addAbsDate.checked)
	{
		addAbsDateLabel.textContent = "Абсолютная дата: год    день.месяц        часы:минуты";
		h.placeholder   = "год";
		m.placeholder   = "день.месяц";
		s.placeholder   = "часы:минуты";
		
		h.style["background-color"] = "yellow";
		m.style["background-color"] = "yellow";
		s.style["background-color"] = "yellow";
	}
	else
	{
		addAbsDateLabel.textContent = "Абсолютная дата";
		h.placeholder = "часы";
		m.placeholder = "минуты";
		s.placeholder = "секунды";

		h.style["background-color"] = "";
		m.style["background-color"] = "";
		s.style["background-color"] = "";
	}
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
	var id;
	if (!timers)
	{
		var ids = [];
		ids.push
		(
			{id: ID}
		);

		ids.push
		(
			{id: getNewId(timersObject.saved)}
		);

		ids.push
		(
			{ id: getNewId(timersObject.timers)}
		);

		id = getNewId(ids)
	}
	else
	{
		id = ID;
		for (var cur of timers)
		{
			if (cur.id >= id)
				id = cur.id + 1;
		}
	}

	ID = id + 1;
	return id;
};

function isSilent()
{
	if (silentEndTime > new Date().getTime())
		return true;

	return false;
}

var silentEndTime = 0;
function play(freq, time, volume, old)
{
	if (isSilent())
		return;

	if (!AC)
		onAudioLoad();

	if (!AC || soundRegime == SoundDisableRegime)
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

	var min = function (val, constraint)
	{
		if (val > constraint)
			return constraint;
		if (val < -constraint)
			return -constraint;

		return val;
	};

	var buffer = AC.createBuffer(1, bufferSize, AC.sampleRate);
	var data = buffer.getChannelData(0);
	var CS   = 500.0;
	var CS2  = 1.0;
	for (var i = 0; i < bufferSize; i++)
	{
		if (old)
		{
			if (old == 1)
				data[i] = volume * Math.sin(i * qw);
			else
			if (old == 2)
				data[i] = volume * min(CS2*Math.sin(i * qw) + CS2/2.0*Math.sin(i * qw*2) + CS2*Math.sin(i * qw/2), 1.0);
		}
		else
		{
			data[i] = volume * min(CS*Math.sin(i * qw) + CS*Math.sin((i + 5) * qw/4) + CS*Math.sin((i + 500) * qw/2), 1.0);
		}
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

function loadSoundRegime()
{
	try
	{
		var soundRegime = localStorage.getItem(timerStorageName + '.soundRegime');
		if (typeof(soundRegime) != "undefined" && soundRegime)
		{
			soundRegimeObject = JSON.parse(soundRegime);

			var btn = document.getElementById("defer1");
			if (!soundRegimeObject.DeferTime)
				soundRegimeObject.DeferTime = 1;

			btn.value = soundRegimeObject.DeferTime + " мин.";
		}
	}
	catch (e)
	{
		console.error(e);
	}
}

function saveSoundRegime()
{
	localStorage.setItem(timerStorageName + '.soundRegime', JSON.stringify(soundRegimeObject));
}


function getSoundRegime()
{
	loadSoundRegime();

	return soundRegimeObject.soundRegime || 0;
}

function setSoundRegime(value)
{
	soundRegimeObject.soundRegime = value;
	saveSoundRegime();
}

function getGainVal()
{
	loadSoundRegime();

	return soundRegimeObject.gainVal ? soundRegimeObject.gainVal : 1.0;
};

function setGainVal(value)
{
	soundRegimeObject.gainVal = value;
	saveSoundRegime();
};

function onAudioLoad()
{
	AC = new AudioContext();

	if (AC == null)
		return null;

	var gainVal = getGainVal();

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


function makeDeferChangeInterval()
{
	if (isNaN(soundRegimeObject.DeferTime))
		soundRegimeObject.DeferTime = 1;

	soundRegimeObject.DeferTime++;
	if (soundRegimeObject.DeferTime > 7)
		soundRegimeObject.DeferTime = 1;
	
	var btn = document.getElementById("defer1");
	btn.value = soundRegimeObject.DeferTime + " мин.";

	saveSoundRegime();
}

function makeDefer()
{
	var DeferTime = soundRegimeObject.DeferTime;

	var minute = 1000 * 60; // Одна минута
	var now    = new Date().getTime();
	var first  = now + minute * DeferTime;
	for (var cur of timersObject.timers)
	{
		if (cur.Important)
			continue;

		if (cur.stopped || cur.endL < first)
		{
			cur.endL     = first;
			cur.deferred = true;
			cur.stopped  = false;

			first += minute * DeferTime;

			// Удаляем уведомления
			try
			{
				var notification = notificationObjects[cur.id];
				if (notification instanceof Notification)
				{
					notification.close();
					delete notificationObjects[cur.id];
				}
			}
			catch (e)
			{
				console.error(e);
			}
		}
	}

	saveTimers();
	drawTimers();
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

function formatTime(date)
{
	var str = 	addNull(date.getHours())
		+ ':' + addNull(date.getMinutes())
		+ ':' + addNull(date.getSeconds());

	return str;
}

var lastDateOfPlay = false;
var ImportantPlay  = false;
function interval()
{
	var now = new Date().getTime();
	var difMin  = 24*60*60*1000;
	var minText = 'Таймер';

	var btn = document.getElementById("silent");
	btn.value = "откл. 1 минута";

	if (silentEndTime > now)
	{
		var dt = new Date(silentEndTime - now);

		btn.value = "отключено " + addNull(dt.getUTCMinutes()) + ":" + addNull(dt.getUTCSeconds());
	}

	var isPlay    = false;
	ImportantPlay = false;
	for (var cur of timersObject.timers)
	{
		var tid = cur.id;

		var tt = document.getElementById('timer-' + tid + '-t');
		var dif = cur.end - now;

		if (dif <= 0 || cur.deferred)
		{
			if (cur.stopped !== true && cur.endL < now)
			{
				cur.deferred = false;
				cur.stopped  = true;
				cur.played   = 0;
				cur.playedA  = 0;

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

				if (cur.deferred != true)
					MakeNotification(cur, cur.text);

				// Если третий режим, то сбрасываем таймер звуков,
				// чтобы новый пользовательский таймер смог снова прозвучать
				if (soundRegime == 3)
				{
					lastDateOfPlay   = Date.now();
					playObject.pause = 0;
				}

				saveTimers();
				drawTimers();
			}

			tt.textContent = '00:00:00';

			var tm = document.getElementById('timer-' + tid + '-del');

			if (cur.deferred)
			{
				tm.style.backgroundColor = '#8888FF';
			}
			else
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

			cur.end = new Date(now + 1000).getTime();
		}

		var end = new Date(dif);

		// Иначе это уже остановленный таймер
		if (cur.stopped !== true)
		{
			tt.textContent = formatDate(new Date(cur.endL - now));

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

		// Если есть хотя бы один остановленный таймер, нужно отметить, что есть звук
		if (cur.stopped === true)
		{
			isPlay = true;
			if (cur.Important)
				ImportantPlay = true;

			// Устанавливаем дату первого запроса именно здесь,
			// т.к. выше после перезагрузки страницы уже может не сработать условие !stopped,
			// т.к. таймер уже остановлен
			if (lastDateOfPlay === false)
				lastDateOfPlay = Date.now();
		}
	}

	document.title = minText;
	setIntervalsWidth();
	
	var timeBox = document.getElementById("timeBox");
	timeBox.textContent = formatTime(new Date());


	// drawTimersShorts работает долго, если будет вызываться каждый раз
	// то элементы могут перестать реагировать на клики пользователя
	if (lastToDeleteSavedTimer !== false)
	if (new Date().getTime() - lastToDeleteSavedTimer >= timerToDeleteInterval)
	{
		setTimeout
		(
			function()
			{
				updateDeleteTextForTimersShorts();
			},
			0
		);
	}

	if (!isPlay)
		lastDateOfPlay = false;

	playGeneral();
};

var lastPlaySound = 0;	// Это дата, когда звук заканчивается
var playObject = 
					{
						state: 0,
						pause: 0
					};

function playGeneral()
{
	var lastTime = Date.now() - lastPlaySound;

	if (!lastDateOfPlay)
	{
		// Если звук уже прошёл, сбрасываем на ноль, чтобы в следующий раз снова начать с большого интервала
		if (lastTime >= 0)
		{
			lastPlaySound = 0;
		}
		playObject.state = 0;
		playObject.pause = 0;

		return;
	}

	
	var Urgent   = Date.now() - lastDateOfPlay;

	// Звук ещё звучит
	if (lastTime < 0)
		return;

	if (Date.now() < playObject.pause)
		return;

	// Обычный звук
	if (soundRegime == 0)
	{
		if (Urgent < 30*1000)
		{
			if (playObject.state == 0)
			{
				play(undefined, undefined, 0.5);
				playObject.state = 1;
				lastPlaySound = Date.now() + 1000;

				return;
			}

			if (lastTime > 9000)
			{
				play();

				lastPlaySound = Date.now() + 1000;
			}
		}
		else
		if (Urgent > 1*60*1000)
		{
			var vol = 1.0;
			if (playObject.state == 0)
			{
				vol = 2.0;
			}
			else
			if (playObject.state > 5)
			{
				playObject.state = -1;
			}

			play(130.813, 2.0, vol, 2);
			lastPlaySound    = Date.now() + 2000;
			playObject.pause = Date.now() + 15*1000;

			playObject.state++;
		}
		else
		{
			// https://soundprogramming.net/file-formats/midi-note-frequencies/
			if (playObject.state <= 0)
				play(440);
			else
			if (playObject.state == 1)
				play(415.305);
			else
			if (playObject.state == 2)
			{
				playObject.pause = Date.now() + 7000;
			}
			else
			if (playObject.state == 3)
				play(349.228);
			else
			if (playObject.state == 4)
				play(329.628);
			else
			if (playObject.state == 5)
			{
				playObject.pause = Date.now() + 30*1000;
			}

			playObject.state++;
			if (playObject.state > 5)
			{
				playObject.state = 0;
			}

			lastPlaySound = Date.now() + 1000;
			return true;
		}
	}
	else
	// Приглушённый звук
	if (soundRegime == 1 || soundRegime == 2)
	{
		play(0, 1.0, 1.0, soundRegime == 2 ? 1 : 0);

		if (playObject.state == 0)
		{
			playObject.pause = Date.now() + 2*1000;
		}
		else
		if (playObject.state == 1)
		{
			playObject.pause = Date.now() + 15*1000;
		}
		else
		{
			playObject.state = -1;
			if (Urgent > 2*60*1000)
				playObject.pause = Date.now() + 60*1000;
			else
				playObject.pause = Date.now() + 30*1000;
		}

		playObject.state++;
	}
	else
	if (soundRegime == 3)
	{
		if (Urgent <= 90*1000 || ImportantPlay)
		{
			play();
			playObject.pause = Date.now() + 60*1000;
		}
	}
}

function onClickToTimer(Element, text)
{
	return function()
	{
		var textElement = document.getElementById("text");
		textElement.value = text;

		hideAlert();
	};
};

function onClickToSavedTimer(Element, timer, addImmediately, timerType)
{
	return function(mouseEvent)
	{
		hideAlert();

		var textElement = document.getElementById("text");
		var val         = timer.name;

		if (timerType == 2)
		if (textElement.value)
			val = textElement.value;

		if (addImmediately || mouseEvent.shiftKey)
		{
			var id = getNewId();
			addTimer(id, 1000*(timer.h*3600 + timer.m*60 + timer.s), val);

			// Контекстное меню не должно появится (здесь - от клика на таймер)
			mouseEvent.preventDefault();
			return true;
		}

		if (timerType != 2)
		if (timer.name)
			textElement.value = timer.name;

		if (timer.h)
			document.getElementById("hours")  .value = timer.h || "";
		
		if (timer.m)
			document.getElementById("minutes").value = timer.m || "";

		if (timer.s)
			document.getElementById("seconds").value = timer.s || "";

		// Контекстное меню не должно появится (здесь - от интервала)
		mouseEvent.preventDefault();
	};
};

function drawTimer(timer)
{
	var main = document.getElementById("main");
	var now  = new Date();

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
	tend.textContent = new Date(timer.endL).toLocaleString();
	tend.style.marginLeft = '10%';
	if (timer.endS && timer.endS != timer.endL)
	{
		tend.textContent = new Date(timer.endS).toLocaleString() + "\t" + tend.textContent;

		if (now.getTime() > timer.endS)
			tend.style.backgroundColor = "#FF8888";
	}

	var tdeldiv = document.createElement("div");
	div.appendChild(tdeldiv);
	tdeldiv.style.marginBottom = '30px';
	tdeldiv.style.marginTop = '15px';

	var tdel = document.createElement("span");
	tdeldiv.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Удалить";
	tdel.addEventListener('click', deleteTimer);
	tdel.id = 'timer-' + timer.id + "-del";
	
	if (isTimerToDelete(timer))
	{
		tdel.textContent = "Точно удалить?";
	}
	else
	{
		timer.toDelete = false;
	}

	var tImportant = document.createElement("span");
	tdeldiv.appendChild(tImportant);
	tImportant.tid = timer.id;
	tImportant.textContent = timer.Important ? "Важная" : "Не важная";
	tImportant.style.color = timer.Important ? "#000000" : "#558855";
	tImportant.addEventListener('click', importantTimer);
	tImportant.id = 'timer-' + timer.id + "-imp";
	tImportant.style.marginLeft = '2%';


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
					addTimer(getNewId(), cur.end, cur.text, true, true);
			}
			catch (e)
			{
				success = false;
				console.error(e);
			}
		}

		for (var cur of t.saved)
		{
			try
			{
				var found = false;
				for (var s of timersObject.saved)
				{
					if (s.isInterval != cur.isInterval)
						continue;

					if (cur.isInterval)
					{
						if (s.totalSeconds == cur.totalSeconds)
						{
							found = true;
							break;
						}
					}
					else
					if (s.name == cur.name)
					{
						found = true;
						break;
					}
				}

				if (!found)
					addSavedTimer(0, cur.h, cur.m, cur.s, cur.name, cur.isInterval, false, cur.isControlTask);
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

function isHighestPriority(a, b)
{
	if (!a.stopped && b.stopped)
		return true;

	if (a.stopped && b.stopped)
	{
		if (!a.Important && b.Important)
			return true;

		if (a.Important && !b.Important)
			return false;
	}

	if (a.endS ? (a.endS > b.endS) : (a.endL > b.endL))
		return true;

	return false;
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
					if (isHighestPriority(t[i], t[j]))
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
				//addTimer(cur.id, cur.end, cur.text, true, true);
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

	drawTimersShorts();
};

function hideAlert()
{
	document.getElementById("alert").style.display = 'none';
	playNull();
};

function playNull()
{
	play(440, 0.1, 0.01);
}

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

		notificationObjects[timer.id] = notification;
		notification.addEventListener
		(
			'click',
			function(event)
			{
				var timers = timersObject.timers;
				for (var curI = 0; curI < timers.length; curI++)
				{
					var cur = timers[curI];
					if (cur.id == timer.id)
					{
						window.focus();

						if (cur.Important)
							return;
					}
				}

				notification.close();
				delete notificationObjects[timer.id];
				window.focus();
/*
				deleteTimer.apply
				(
					{
						tid: timer.id
					}
				);*/
			},
			false
		);

		notification.addEventListener
		(
			'close',
			function(event)
			{
				delete notificationObjects[timer.id];
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

function addSavedTimer(id, h, m, s, timerName, savedInterval, toDelete, isControlTask)
{
	if (!timersObject.saved)
		timersObject.saved = [];

	var seconds = h*3600 + m*60 + s;
	var date = new Date(seconds*1000);
	if (savedInterval)
	{
		timerName = formatDateMinimal(date);
	}

	var newTimer =
		{
			h:  h,
			m:  m,
			s:  s,
			id: id || getNewId(),

			totalSeconds:  seconds,
			name:          timerName,
			timeVal:       formatDate(date),
			isInterval:    savedInterval,
			toDelete:      toDelete || false,
			isControlTask: isControlTask || false
		};

	timersObject.saved.push(newTimer);

	return newTimer;
}

var nameOfControlTaskAlertNode = 'ControlTasks-NotRepresented';
function drawSavedTimer(timer)
{
	// var main = document.getElementById("timersShort");
	var main = timer.isControlTask === true ? document.getElementById("ControlTasks") : document.getElementById("timersShort");

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

	if (timer.totalSeconds > 0)
	{
		var tend = document.createElement("span");
		tc.appendChild(tend);
		tend.id = 'timer-' + timer.id + "-end";
		tend.textContent = formatDate(new Date(timer.totalSeconds*1000));
		//tend.style.marginLeft = '10%';
	}

	var tdeldiv = document.createElement("div");
	div.appendChild(tdeldiv);
/*	tdeldiv.style.marginBottom = '30px';
	tdeldiv.style.marginTop = '15px';
*/
	// span - чтобы "Удалить" не растягивалась на всю страницу по ширине
	var tdel = document.createElement("span");
	tdeldiv.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.textContent = "Удалить";
	tdel.addEventListener('click', deleteSavedTimer);
	tdel.id = 'timer-' + timer.id + "-del";

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

	if (timer.isControlTask === true)
	{
		var isNotRepresented = true;
		var timers = timersObject.timers;
		for (var curI = 0; curI < timers.length; curI++)
		{
			var cur = timers[curI];
			if (cur.text == timer.name)
			{
				isNotRepresented = false;
				break;
			}
		}

		if (isNotRepresented)
		{
			div.style["background-color"] = "yellow";

			var el = document.getElementById(nameOfControlTaskAlertNode);
			var tn = document.getElementById("timersName");

			if (!el)
			{
				el    = document.createElement("div");
				el.id = nameOfControlTaskAlertNode;
				el.style["background-color"] = "yellow";
				el.textContent = "В списке таймеров не хватает задач из контрольного списка";

				tn.parentNode.insertBefore(el, tn);
			}

			// el.textContent += "\r\n" + timer.name;
			var ctel = document.createElement("div");
			el.appendChild(ctel);
			ctel.textContent = timer.name;
			ctel.addEventListener
			(
				'click',
				function()
				{
					document.getElementById("text").value = this.textContent;
				}
			);
		}
	}
}

function drawSavedInterval(timer)
{
	var main = document.getElementById("timersIntervalShort");

	var div  = document.createElement("span");
	div.id   = 'savedtimer-' + timer.id;
	div.classList.add('nowrap');
	main.appendChild(div);

	var te   = document.createElement("input");
	te.type = "button";
	div.appendChild(te);
	te.value = timer.name;
	te.addEventListener('click',       onClickToSavedTimer(te, timer, true , 2));
	te.addEventListener('contextmenu', onClickToSavedTimer(te, timer, false, 2));
	// te.style.marginLeft = '5%';

	var tdel = document.createElement("input");
	tdel.type = "button";
	div.appendChild(tdel);
	tdel.tid = timer.id;
	tdel.value = "X";
	tdel.style["background-color"] = "red";
	tdel.addEventListener('click', deleteSavedTimer);
	tdel.id = 'timer-' + timer.id + "-del";

	if (isTimerToDelete(timer))
	{
		tdel.value = "Удалить?";
	}
	else
	{
		timer.toDelete = false;
	}

	var hr = document.createElement("span");
	hr.textContent = " ";
	main.appendChild(hr);
}

function setIntervalsWidth()
{
	var main      = document.getElementById("timersShort");
	var intervals = document.getElementById("timersIntervalShort");

	intervals.style.width = document.body.clientWidth - main.clientWidth;
}

// Эта функция работает быстрее, поэтому нет проблем с тем, что таймер может не реагировать при его перерисовке
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

function drawTimersShorts()
{
	var main = document.getElementById("timersShort");
	main.textContent = "";
	
	var CT = document.getElementById("ControlTasks");
	CT.textContent = "";
	
	var CT_alert = document.getElementById(nameOfControlTaskAlertNode);

	if (CT_alert)
	{
		CT_alert.parentNode.removeChild(CT_alert);
	}

	var intervals = document.getElementById("timersIntervalShort");
	intervals.textContent = "";

	// Чтобы таймеры постоянно не перерисовывались, очищаем lastToDeleteSavedTimer
	lastToDeleteSavedTimer = false;

	var isControlTask = false;

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
					var newTimer = addSavedTimer(cur.id, cur.h, cur.m, cur.s, cur.name, cur.isInterval, cur.toDelete, cur.isControlTask);

					if (cur.isControlTask && !isControlTask)
					{
						isControlTask = true;
						var div  = document.createElement("div");
						div.id   = 'isControlTask-separator';
						div.textContent = "Контрольные задачи";

						CT.appendChild(document.createElement("hr"));
						CT.appendChild(div);
						CT.appendChild(document.createElement("hr"));
					}

					if (newTimer.isInterval)
						drawSavedInterval(newTimer);
					else
						drawSavedTimer(newTimer);

					// Устанавливаем необходимость перерисовки таймеров, если это необходимо
					// Делаем это после прорисовки,
					// потому что при прорисовке устаревшие значения toDelete удаляются
					if (newTimer.toDelete)
						lastToDeleteSavedTimer = newTimer.toDelete;

				}
			}
		}
		else
		{
			timersObject.saved = [];
		}
	}

	setTimeout(setIntervalsWidth, 0);
};

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
	
	btn = document.getElementById("addControlTask");
	btn.addEventListener('click', addControlTask);

	/*
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
*/
	btn = document.getElementById("alert");
	btn.addEventListener('click', hideAlert);

	btn = document.getElementById("addAbsDate");
	btn.addEventListener('click', addAbsDateClicked);

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

				setGainVal(this.value);
			}
		}
	);

	btn = document.getElementById("gainVal");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			if (me.ctrlKey && me.altKey)
				play(0, 1.0, 1.0, 1);
			else
			if (me.ctrlKey)
				play(660);
			else
			if (me.altKey)
				play(130.813, 2.0, 1.0, 2);
			else
				play();
		}
	);

	soundRegime  = getSoundRegime();
	soundSwither = document.getElementById("soundSwither");
	soundSwither.textContent = getSoundRegimeText(soundRegime);
	soundSwither.style["font-weight"] = soundRegime == SoundDisableRegime ? "bold" : "normal";
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

			setSoundRegime(soundRegime);
			soundSwither.textContent = getSoundRegimeText(soundRegime);
			soundSwither.style["font-weight"] = soundRegime == SoundDisableRegime ? "bold" : "normal";
		}
	);

	var gainVal = getGainVal();

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

	// Добавляет минуту к времени выключения звука таймера
	btn = document.getElementById("silent1");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			if (silentEndTime > new Date().getTime())
				silentEndTime = silentEndTime + 60*1000;
			else
				silentEndTime = new Date().getTime() + 60*1000;
		}
	);
	
	btn = document.getElementById("defer");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			makeDefer();
		}
	);
	
	btn = document.getElementById("defer1");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			makeDeferChangeInterval();
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
	
	btn = document.getElementById("resetTime");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			document.getElementById("hours")  .value = '';
			document.getElementById("minutes").value = '';
			document.getElementById("seconds").value = '';
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

			addSavedTimer(0, h, m, s, timerName, false);
			saveTimers();
			drawTimersShorts();
		}
	);
	
	
	btn = document.getElementById("saveInterval");
	btn.addEventListener
	(
		'click',
		function(me)
		{
			var h = parseFloat(document.getElementById("hours")  .value || 0);
			var m = parseFloat(document.getElementById("minutes").value || 0);
			var s = parseFloat(document.getElementById("seconds").value || 0);

			var timerName = ""; // document.getElementById("text").value;

			addSavedTimer(0, h, m, s, timerName, true);
			saveTimers();
			drawTimersShorts();
		}
	);
	
	
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
			/*
			
function saveTimers()
{
	localStorage.setItem(timerStorageName, JSON.stringify(timersObject));
};

function drawTimers()
{
	var main = document.getElementById("main");
	main.textContent = "";

	var timersFromStorage = localStorage.getItem(timerStorageName);
	if (typeof(timersFromStorage) != "undefined" && timersFromStorage)
	{
		var t = JSON.parse(timersFromStorage);
			*/

            try
            {
                navigator.permissions.query
                ({name: 'clipboard-read'})
                .then
                (
                    function(result)
                    {
                        if (result.state == 'granted' || result.state == 'prompt')
                        {
                        }
                        else
                        {
                            console.error("clipboard-read permission not granted: " + result.state);
                        }
                    }
                );
            }
            catch (e)
            {
                console.error(e);
            }

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


	// audio = document.getElementById("audio");

	drawTimers();
	InitializeNotification();

	setInterval
	(
		interval,
		100
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
