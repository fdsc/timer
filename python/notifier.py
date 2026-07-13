import subprocess
import threading
from datetime import datetime
from typing import Any, List
from pathlib import Path

MEDIA_PATHS: List[str] = []

# Глобальное состояние: отслеживаем активные notify-send с флагом -w
_active_notify_handles = set()

def _run_notify_with_wait(title: str, message: str, task_id, urgency: str = "normal", icon_path: str | None = None) -> bool:
    """
    Запускает notify-send -w в отдельном потоке, чтобы не блокировать GUI.
    Возвращает True, если команда успешно запущена; завершение ожидания
    обрабатывается внутри потока через clear_pending_after_notify.
    task_id передаётся через замыкание (захватывается из внешней области).
    """
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
            _active_notify_handles.add(proc.pid)
            proc.wait()  # ждём, пока пользователь закроет уведомление
            _active_notify_handles.discard(proc.pid)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        finally:
            # clear_pending_after_notify должен быть вызван с нужным task_id
            if hasattr(run_and_clear, "task_id"):
                _pending_alert_tasks.discard(run_and_clear.task_id)

    # task_id «пробрасываем» через атрибут функции — это простой способ передать его в поток
    run_and_clear.task_id = task_id

    try:
        t = threading.Thread(target=run_and_clear, daemon=True)
        t.start()
        return True
    except Exception:
        traceback.print_exc()
        return False


def notify(title: str, message: str, task_id, urgency: str = "normal", icon_path: str | None = None) -> bool:
    return _run_notify_with_wait(title, message, task_id, urgency, icon_path)


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

    # Вызов show_bulk_critical_alert автоматически, если вернул True
    if task_obj.parent.check_bulk_alerts(len(_pending_alert_tasks)):
        return

    text = getattr(task_obj, "text", "Неизвестная задача")
    is_important = bool(getattr(task_obj, "is_important", False))
    alert_time = getattr(task_obj, "alert_time", None)
    volume_factor = getattr(task_obj.parent, "volume_factor", 1.0)
    task_id = getattr(task_obj, "task_id", None)

    # Не показываем новое уведомление, если для этой задачи уже есть незакрытое
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

    play_sound(sound_file, volume_factor)

    # Помечаем задачу как «в ожидании подтверждения закрытия»
    _pending_alert_tasks.add(task_id)

    # Используем notify с ожиданием (-w)
    if not notify(title, message, task_id, urgency=urgency_level):
        # Если notify-send недоступен или не сработал — fallback без ожидания
        fallback_messagebox(title, message)
        _pending_alert_tasks.discard(task_id)
    else:
        pass


def show_bulk_critical_alert(app, tasks_list, icon_path: str | None = None) -> None:
    """
    Выводит одно оповещение critical, когда задач слишком много (>2).
    В сообщение включается отсортированный список задач (по важности, затем по просрочке).
    Добавляет картинку, которая характеризует то, что задач слишком много.
    """
    # Сортировка: сначала важные, потом по возрастанию просрочки (т.е. самые просроченные — первыми)
    def sort_key(task):
        is_important = bool(getattr(task, "is_important", False))
        alert_time = getattr(task, "alert_time", None)
        overdue = 0
        if alert_time is not None:
            delta = datetime.now() - alert_time
            overdue = max(0, int(delta.total_seconds()))
        # Сначала важные (True > False), затем большая просрочка
        return (not is_important, -overdue)

    sorted_tasks = sorted(tasks_list, key=sort_key)

    # Формируем список задач для сообщения
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

    message = "Много задач! Проверьте список:\n\n" + "\n".join(lines[:20])  # максимум 20 задач в уведомлении
    if len(sorted_tasks) > 20:
        message += f"\n\n... и ещё {len(sorted_tasks) - 20} задач."

    title = "⚠️ МНОГО ЗАДАЧ!"

    sound_file = "/usr/share/sounds/freedesktop/stereo/audio-volume-high.oga"
    if MEDIA_PATHS and len(MEDIA_PATHS) > 3:
        sound_file = MEDIA_PATHS[3]

    volume_factor = getattr(app, "volume_factor", 1.0)
    play_sound(sound_file, volume_factor)

    # Не показываем, если уже есть активное notify-send -w
    task_id = -1
    if task_id in _pending_alert_tasks:
        return

    _pending_alert_tasks.add(task_id)

    ok = notify(title, message, task_id, urgency="critical", icon_path=icon_path)
    if not ok:
        # Fallback: messagebox, но он не умеет ждать закрытия так же, как notify-send -w.
        # Для простоты используем обычный messagebox без сложной логики таймера здесь.
        try:
            import tkinter.messagebox as mb
            mb.showwarning(title, message)
            _pending_alert_tasks.discard(task_id)
        except Exception:
            pass
