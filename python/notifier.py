import subprocess
from datetime import datetime
from typing import Any

def notify(title: str, message: str, urgency: str = "normal") -> bool:
    """Отправляет уведомление через notify-send с указанным уровнем срочности."""
    try:
        cmd = ["notify-send", "-u", urgency, title, message]
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def fallback_messagebox(title: str, message: str) -> None:
    """Запасной вариант: tkinter.messagebox."""
    import tkinter.messagebox as mb
    mb.showinfo(title, message)

def _calculate_urgency(is_important: bool, overdue_seconds: int) -> str:
    """
    Логика уровней срочности:
      - Обычная: <= 5 мин → low, > 5 мин → normal
      - Важная:   <= 5 мин → normal, > 5 мин → critical
    """
    THRESHOLD_SEC = 300  # 5 минут

    if is_important:
        return "critical" if overdue_seconds > THRESHOLD_SEC else "normal"
    else:
        return "normal" if overdue_seconds > THRESHOLD_SEC else "low"

def show_alert(task_obj: Any) -> None:
    """
    Умное оповещение: принимает только объект задачи.
    
    notifier сам:
      1. Вычисляет просрочку по task_obj.alert_time
      2. Определяет urgency на основе важности и просрочки
      3. Формирует заголовок и сообщение
      4. Отправляет уведомление
    
    Ожидается, что task_obj имеет атрибуты:
      - text: описание задачи
      - is_important: булево
      - alert_time: datetime (время, когда задача должна сработать)
    """
    # Получаем данные из объекта
    text = getattr(task_obj, "text", "Неизвестная задача")
    is_important = bool(getattr(task_obj, "is_important", False))
    alert_time = getattr(task_obj, "alert_time", None)

    # Вычисляем просрочку
    if alert_time is None:
        # Если времени нет — считаем, что просрочки нет (или это ошибка)
        overdue_seconds = 0
    else:
        delta = datetime.now() - alert_time
        overdue_seconds = max(0, int(delta.total_seconds()))

    # Определяем urgency
    urgency_level = _calculate_urgency(is_important, overdue_seconds)

    # Формируем сообщение
    if is_important:
        base_title = "❗ ВАЖНАЯ ЗАДАЧА"
        extra_msg = "Требуется внимание."
    else:
        base_title = "Задача"
        extra_msg = "Время вышло."

    if overdue_seconds > 0:
        minutes, secs = divmod(overdue_seconds, 60)
        time_diff_str = f"{minutes} мин {secs} сек назад"
        message = f"{extra_msg}\nЗадача: {text}\nПросрочено: {time_diff_str}"
    else:
        message = f"{extra_msg}\nЗадача: {text}"

    title = f"{base_title}"

    # Отправляем
    if not notify(title, message, urgency=urgency_level):
        fallback_messagebox(title, message)
