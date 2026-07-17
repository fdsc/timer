import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
from task_block_tasks import TaskType

DEFAULT_TASK = {
    "task_id": "",
    "text": "ошибка загрузки",
    "alert_time": None,          # будет заменено на текущее время при загрузке
    "is_important": False,
    "type": TaskType.NORMAL,
}

def datetime_to_iso(dt: Optional[datetime]) -> str:
    """Конвертирует datetime в ISO 8601 строку. Если None — возвращает пустую строку."""
    if dt is None:
        return ""
    return dt.isoformat()

def iso_to_datetime(s: str) -> Optional[datetime]:
    """Конвертирует ISO 8601 строку в datetime. Если строка пустая или невалидная — возвращает None."""
    if not s:
        return None
    try:
        # fromisoformat поддерживает большинство ISO-форматов
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def get_tasks_dir(data_dir: Path) -> str:
    return data_dir / "tasks"

def ensure_tasks_dir(data_dir: Path) -> bool:
    """Создаёт папку tasks внутри data_dir. Возвращает True при успехе, False при ошибке."""
    tasks_dir = get_tasks_dir(data_dir)
    try:
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        print(f"[tasks_storage] Ошибка создания папки tasks: {e}")
        return False

def _load_task_from_file(file_path: Path, current_time: datetime) -> Dict[str, Any]:
    """Загружает одну задачу из файла. Если файл повреждён или неполный — возвращает аварийную задачу."""
    result = DEFAULT_TASK.copy()
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"[tasks_storage] Ошибка чтения/парсинга файла {file_path}: {e}")
        result["alert_time"] = current_time
        return result

    # Заполняем только те поля, которые есть, остальные остаются по умолчанию
    if "task_id" in data and isinstance(data["task_id"], str):
        result["task_id"] = data["task_id"]
    if "text" in data and isinstance(data["text"], str):
        result["text"] = data["text"]
    else:
        result["text"] = "ошибка загрузки"

    if "is_important" in data:
        result["is_important"] = bool(data["is_important"])

    # Обрабатываем как старые, так и новые значения
    if 'type' in data:
        result["type"] = TaskType(data["type"])
    elif "is_quiet" in data:
        result["type"] = TaskType.QUIET if bool(data["is_quiet"]) else TaskType.NORMAL
    else:
        result["type"] = TaskType.NORMAL

    # alert_time: если есть валидная строка — парсим, иначе ставим текущее время
    raw_alert = data.get("alert_time")
    if isinstance(raw_alert, str):
        parsed = iso_to_datetime(raw_alert)
        if parsed is not None:
            result["alert_time"] = parsed
        else:
            print(f"[tasks_storage] Невалидный alert_time в файле {file_path}, используем текущее время.")
            result["alert_time"] = current_time
    else:
        print(f"[tasks_storage] Отсутствует alert_time в файле {file_path}, используем текущее время.")
        result["alert_time"] = current_time

    return result

def load_all_tasks(data_dir: Path, lock: threading.Lock) -> List[Dict[str, Any]]:
    """
    Загружает все задачи из папки tasks.
    - Файлы с некорректными именами (не только цифры) игнорируются (с логированием).
    - Повреждённые или неполные файлы загружаются как аварийные задачи.
    """
    tasks_dir = get_tasks_dir(data_dir)
    loaded_tasks = []
    current_time = datetime.now()

    try:
        entries = list(tasks_dir.iterdir())
    except OSError as e:
        print(f"[tasks_storage] Ошибка доступа к папке tasks: {e}")
        return []

    for entry in entries:
        if not entry.is_file():
            continue
        if entry.suffix.lower() != ".json":
            continue

        file_name = entry.name[:-5]  # убираем .json

        with lock:
            task_data = _load_task_from_file(entry, current_time)
            loaded_tasks.append(task_data)

    return loaded_tasks

def save_task(data_dir: Path, task_data: Dict[str, Any], lock: threading.Lock, io_error_flag: bool) -> bool:
    """
    Сохраняет одну задачу в файл.
    Если io_error_flag == True — ничего не делает, возвращает False.
    alert_time=None заменяется на текущее время перед сохранением.
    Возвращает True при успехе, False при ошибке.
    """
    if io_error_flag:
        return False

    task_id = task_data.get("task_id")
    if not task_id or not isinstance(task_id, str):
        print("[tasks_storage] Недопустимый task_id для сохранения.")
        return False

    tasks_dir = get_tasks_dir(data_dir)
    file_path = tasks_dir / f"{task_id}.json"

    # Подготавливаем данные для сохранения
    save_data = {
        "task_id":      task_id,
        "text":         task_data.get("text", ""),
        "is_important": bool(task_data.get("is_important", False)),
        "type":         task_data["type"],
    }

    # Если alert_time None — ставим текущее время, иначе конвертируем в ISO
    alert = task_data.get("alert_time")
    if alert is None:
        alert = datetime.now()
    save_data["alert_time"] = datetime_to_iso(alert)

    with lock:
        try:
            # Гарантируем существование папки
            tasks_dir.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True
        except OSError as e:
            print(f"[tasks_storage] Ошибка записи файла {file_path}: {e}")
            return False

def delete_task_file(data_dir: Path, task_id: str, lock: threading.Lock, io_error_flag: bool) -> bool:
    """
    Удаляет файл задачи. Если файла нет — это не ошибка.
    Если io_error_flag == True — ничего не делает.
    Возвращает True, если операция была выполнена (или файл отсутствовал), False при ошибке доступа.
    """
    if io_error_flag or not task_id:
        return False

    tasks_dir = get_tasks_dir(data_dir)
    file_path = tasks_dir / f"{task_id}.json"

    with lock:
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except OSError as e:
            print(f"[tasks_storage] Ошибка удаления файла {file_path}: {e}")
            return False


