import os
import signal
import subprocess
import threading
from datetime import datetime
from typing import Any, List
from pathlib import Path
import traceback


MEDIA_PATHS: List[str] = []

# Глобальное состояние: отслеживаем активные notify-send с флагом -w
_active_notify_handles = {}

_general_sound_timeout = 60*1000
BULK_TASK_ID = -1
_state_lock  = threading.RLock()



def _on_notify_finished(task_id: int, app: Any | None) -> None:
    """
    Вызывается после завершения notify-send.
    Удаляет задачу из очереди и проверяет особые условия для BULK_TASK_ID.
    """
    with _state_lock:
        _pending_alert_tasks.discard(task_id)

        # Проверка: если в очереди осталась ровно одна задача и это BULK_TASK_ID
        if len(_pending_alert_tasks) == 1 and BULK_TASK_ID in _pending_alert_tasks:
            cancel_notify_for_task(BULK_TASK_ID)

        # Стандартная проверка: если очередь пуста — сбрасываем состояние общего сигнала
        if app is not None and len(_pending_alert_tasks) == 0:
            reset_alert_sound_state(app)


def _run_notify_with_wait(title: str, message: str, task_id, app: Any, urgency: str = "normal", icon_path: str | None = None) -> bool:
    cmd = ["notify-send", "-u", urgency, "-w"]
    if icon_path and Path(icon_path).exists():
        cmd.extend(["-i", icon_path])
    cmd.extend([title, message])

    def run_and_clear():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _active_notify_handles[task_id] = proc.pid
            proc.wait()
            _active_notify_handles.pop(task_id, None)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        finally:
            _on_notify_finished(task_id, app)

    try:
        t = threading.Thread(target=run_and_clear, daemon=True)
        t.start()
        return True
    except Exception:
        traceback.print_exc()
        return False

def cancel_notify_for_task(task_id):
    """Убивает notify-send для конкретного task_id (если запущен с -w)."""
    pid = _active_notify_handles.pop(task_id, None)
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        pass  # уже завершился
    except Exception:
        traceback.print_exc()

def notify(title: str, message: str, task_id, app: Any | None, urgency: str = "normal", icon_path: str | None = None) -> bool:
    return _run_notify_with_wait(title, message, task_id, app, urgency, icon_path)


def _play_sound_async(sound_path: str, volume_factor: float = 1.0) -> None:
    if not sound_path or not Path(sound_path).exists():
        return
    try:
        cmd = ["play", "-q", sound_path, "vol", str(volume_factor)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def play_sound(sound_path: str, volume_factor: float = 1.0) -> None:
    thread = threading.Thread(target=_play_sound_async, args=(sound_path, volume_factor), daemon=True)
    thread.start()

def play_low_tone(volume_factor: float = 1.0) -> None:
    play_sound(MEDIA_PATHS[4], volume_factor)

def fallback_messagebox(title: str, message: str) -> None:
    import tkinter.messagebox as mb
    mb.showinfo(title, message)


def _calculate_urgency(is_important: bool, overdue_seconds: int) -> str:
    THRESHOLD_SEC = 300
    if is_important:
        return "critical" if overdue_seconds > THRESHOLD_SEC else "normal"
    else:
        return "normal" if overdue_seconds > THRESHOLD_SEC else "low"


# Храним задачи, для которых уже показано уведомление и оно ещё не закрыто
_pending_alert_tasks = set()


def show_alert(task_obj: Any) -> None:
    app = task_obj.parent  # это экземпляр App

    # Если bulk-оповещение сработало — прерываем показ отдельного
    with _state_lock:
        if app.check_bulk_alerts(len(_pending_alert_tasks)):
            return

    text = getattr(task_obj, "text", "Неизвестная задача")
    is_important = bool(getattr(task_obj, "is_important", False))
    alert_time = getattr(task_obj, "alert_time", None)
    volume_factor = getattr(app, "volume_factor", 1.0)
    task_id = getattr(task_obj, "task_id", None)

    with _state_lock:
        if task_id in _pending_alert_tasks:
            return

    if alert_time is None:
        overdue_seconds = 0
    else:
        delta = datetime.now() - alert_time
        overdue_seconds = max(0, int(delta.total_seconds()))

    urgency_level = _calculate_urgency(is_important, overdue_seconds)
    base_title = "❗ ВАЖНАЯ ЗАДАЧА" if is_important else "Задача"

    if overdue_seconds > 0:
        minutes, secs = divmod(overdue_seconds, 60)
        time_diff_str = f"{minutes} мин {secs} сек назад"
        message = f"Задача: {text}\nПросрочено: {time_diff_str}"
    else:
        message = f"Задача: {text}"

    title = base_title

    sound_file = "/usr/share/sounds/freedesktop/stereo/complete.oga"
    if MEDIA_PATHS:
        idx = -1
        if not is_important and overdue_seconds == 0:
            idx = 0
        elif not is_important and overdue_seconds > 0:
            idx = 1
        elif is_important and overdue_seconds == 0:
            idx = 2
        elif is_important and overdue_seconds > 0:
            idx = 3

        if 0 <= idx < len(MEDIA_PATHS):
            sound_file = MEDIA_PATHS[idx]

    # --- ЛОГИКА ОБЩЕЙ СИГНАЛИЗАЦИИ ---

    # 1. Если очередь была пустой, фиксируем момент появления первой активной задачи
    with _state_lock:
        if len(_pending_alert_tasks) == 0:
            state = app.alert_sound_state
            state["first_pending_add_time"] = datetime.now()
            state["is_general_mode_active"] = False
            # Если был таймер — сбрасываем его на всякий случай
            if state["general_sound_timer_id"] is not None:
                app.root.after_cancel(state["general_sound_timer_id"])
                state["general_sound_timer_id"] = None

        # 2. Проверяем, нужно ли активировать общий режим
        maybe_activate_general_mode(app)

        # 3. Если общий режим активен — НЕ проигрываем индивидуальный звук
        state = app.alert_sound_state
        if not state["is_general_mode_active"]:
            # Проигрываем индивидуальный звук, если общий режим выключен
            play_sound(sound_file, volume_factor)
        # Иначе — индивидуальный звук пропускаем, общий будет проигрываться раз в минуту

        _pending_alert_tasks.add(task_id)

        ok = notify(title, message, task_id, app, urgency=urgency_level)
        if not ok:
            fallback_messagebox(title, message)
            _pending_alert_tasks.discard(task_id)
            # При fallback тоже нужно проверить, не стала ли очередь пустой
            if len(_pending_alert_tasks) == 0:
                reset_alert_sound_state(app)


def show_bulk_critical_alert(app, tasks_list, icon_path: str | None = None) -> None:
    """
    Выводит одно оповещение critical, когда задач слишком много (>2).
    В сообщение включается отсортированный список задач (по важности, затем по просрочке).
    Добавляет картинку, которая характеризует то, что задач слишком много.
    """
    # Сортировка: сначала важные, потом по убыванию просрочки
    def sort_key(task):
        is_important = bool(getattr(task, "is_important", False))
        alert_time = getattr(task, "alert_time", None)
        overdue = 0
        if alert_time is not None:
            delta = datetime.now() - alert_time
            overdue = max(0, int(delta.total_seconds()))
        return (not is_important, -overdue)

    sorted_tasks = sorted(tasks_list, key=sort_key)

    lines = []
    for t in sorted_tasks:
        text = getattr(t, "text", "Неизвестная задача")
        alert_time = getattr(t, "alert_time", None)
        overdue_sec = 0
        if alert_time is not None:
            delta = datetime.now() - alert_time
            overdue_sec = max(0, int(delta.total_seconds()))
        mins, secs = divmod(overdue_sec, 60)
        hrs, mins = divmod(mins, 60)
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        prefix = "❗" if getattr(t, "is_important", False) else "•"
        lines.append(f"{prefix} {text} (просрочка: {time_str})")

    message = "Много задач! Проверьте список:\n\n" + "\n".join(lines[:20])
    if len(sorted_tasks) > 20:
        message += f"\n\n... и ещё {len(sorted_tasks) - 20} задач."

    title = "⚠️ МНОГО ЗАДАЧ!"

    sound_file = "/usr/share/sounds/freedesktop/stereo/audio-volume-high.oga"
    if MEDIA_PATHS and len(MEDIA_PATHS) > 3:
        sound_file = MEDIA_PATHS[3]

    volume_factor = getattr(app, "volume_factor", 1.0)
    play_sound(sound_file, volume_factor)

    task_id = BULK_TASK_ID  # специальный ID для bulk-оповещения
    with _state_lock:
        if task_id in _pending_alert_tasks:
            return

        _pending_alert_tasks.add(task_id)

        ok = notify(title, message, task_id, app, urgency="critical", icon_path=icon_path)
        if not ok:
            try:
                import tkinter.messagebox as mb
                mb.showwarning(title, message)
                _pending_alert_tasks.discard(task_id)
                if len(_pending_alert_tasks) == 0:
                    reset_alert_sound_state(app)
            except Exception:
                pass


# -----------------------------------------------------------------------------
# Хелперы для управления состоянием общего фонового сигнала (логика в App)
# -----------------------------------------------------------------------------

def reset_alert_sound_state(app: Any) -> None:
    """
    Сбрасывает состояние общего фонового сигнала, когда очередь активных задач пуста.
    Вызывается из _run_notify_with_wait после discard(task_id), если очередь стала пустой.
    """
    state = app.alert_sound_state
    state["first_pending_add_time"] = None
    state["is_general_mode_active"] = False
    if state["general_sound_timer_id"] is not None:
        app.root.after_cancel(state["general_sound_timer_id"])
        state["general_sound_timer_id"] = None


def maybe_activate_general_mode(app: Any) -> bool:
    """
    Проверяет, нужно ли один раз включить общий режим.
    Возвращает True, если режим был только что активирован.
    Условия: очередь не пуста, есть first_pending_add_time, прошло >180 сек, режим ещё не активен.
    """
    state = app.alert_sound_state
    with _state_lock:
        if not _pending_alert_tasks:
            return False

    if state["first_pending_add_time"] is None:
        return False

    elapsed = (datetime.now() - state["first_pending_add_time"]).total_seconds()
    if elapsed <= 180:
        return False

    if state["is_general_mode_active"]:
        return False

    # Включаем режим
    state["is_general_mode_active"] = True

    # Запускаем таймер для периодического проигрывания общего звука
    def tick():
        check_and_play_general_sound(app)

    if state["general_sound_timer_id"] is None:
        state["general_sound_timer_id"] = app.root.after(_general_sound_timeout, tick)

    return True


def check_and_play_general_sound(app: Any) -> None:
    """
    Вызывается раз в 60 секунд. Если общий режим активен и есть активные задачи —
    проигрывает общий звук (MEDIA_PATHS[4]). Если очередь пуста — останавливает таймер.
    """
    state = app.alert_sound_state

    with _state_lock:
        if not _pending_alert_tasks:
            # Очередь пуста: сбрасываем состояние и останавливаем таймер
            reset_alert_sound_state(app)
            return

        if not state["is_general_mode_active"]:
            # Режим ещё не включён — ничего не делаем; возможно, включится позже в maybe_activate_general_mode
            return

        # Проигрываем общий звук
        volume_factor = getattr(app, "volume_factor", 1.0)
        sound_file = MEDIA_PATHS[4] if len(MEDIA_PATHS) > 4 else None
        if sound_file and Path(sound_file).exists():
            play_sound(sound_file, volume_factor)

        # Планируем следующий тик
        state["general_sound_timer_id"] = app.root.after(_general_sound_timeout, lambda: check_and_play_general_sound(app))

