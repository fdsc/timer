import os
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

CONFIG_STORE_PATH = Path.home() / ".config" / "vinny-task-tracker" / "config_store.json"
MEDIA_CONFIG_PATH = None  # будет установлено после получения data_dir
DEFAULT_VOLUME = 100

def get_user_data_dir() -> Path:
    """
    Если путь к данным уже сохранён — возвращает его.
    Иначе открывает диалог выбора папки, сохраняет выбор и возвращает путь.
    Создаёт папку, если её нет.
    """
    global MEDIA_CONFIG_PATH

    # Проверяем, есть ли сохранённый путь
    if CONFIG_STORE_PATH.exists():
        try:
            with open(CONFIG_STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                saved_path = Path(data.get("data_dir"))
                if saved_path.exists():
                    MEDIA_CONFIG_PATH = saved_path / "media_config.txt"
                    return saved_path
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Диалог выбора папки
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    initial_dir = str(Path.home())
    data_dir = filedialog.askdirectory(
        title="Выберите папку для хранения задач и настроек",
        initialdir=initial_dir
    )
    root.destroy()

    if not data_dir:
        data_dir = str(Path.home() / ".local" / "share" / "task-tracker")

    data_dir_path = Path(data_dir).expanduser().resolve()
    data_dir_path.mkdir(parents=True, exist_ok=True)

    MEDIA_CONFIG_PATH = data_dir_path / "media_config.txt"

    CONFIG_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"data_dir": str(data_dir_path)}, f, ensure_ascii=False, indent=2)

    return data_dir_path


def load_or_create_opts(data_dir: Path) -> dict:
    opts_path = data_dir / "opts.json"
    default_opts = {"volume_percent": DEFAULT_VOLUME}

    if opts_path.exists():
        try:
            with open(opts_path, "r", encoding="utf-8") as f:
                opts = json.load(f)
        except json.JSONDecodeError:
            opts = {}
    else:
        opts = {}

    if "volume_percent" not in opts:
        opts["volume_percent"] = DEFAULT_VOLUME

    if not opts_path.exists() or "volume_percent" not in json.load(open(opts_path, "r", encoding="utf-8")) if opts_path.exists() else True:
        with open(opts_path, "w", encoding="utf-8") as f:
            json.dump(opts, f, ensure_ascii=False, indent=2)

    return opts


def save_opts(data_dir: Path, opts: dict) -> None:
    opts_path = data_dir / "opts.json"
    with open(opts_path, "w", encoding="utf-8") as f:
        json.dump(opts, f, ensure_ascii=False, indent=2)


def init_media_config(data_dir: Path) -> Path:
    """
    Создаёт media_config.txt, если его нет.
    Формат: одна строка — один путь к файлу.
    Строки по порядку:
      1. звук для обычной непросроченной задачи
      2. звук для обычной просроченной задачи
      3. звук для важной непросроченной задачи
      4. звук для важной просроченной задачи
    Если файл уже есть — не перезаписывает, но гарантирует, что он существует.
    Возвращает путь к файлу.
    """
    media_path = data_dir / "media.conf"

    if media_path.exists():
        return media_path

    # Дефолтные пути (можно заменить на любые, которые реально есть в системе)
    defaults = [
        "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
        "/usr/share/sounds/freedesktop/stereo/suspend-error.oga",
        "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
    ]

    with open(media_path, "w", encoding="utf-8") as f:
        for line in defaults:
            f.write(line + "\n")

    return media_path


def load_media_paths(media_config_path: Path):
    """
    Загружает пути из media_config.txt.
    Возвращает список строк (пустые строки и комментарии можно игнорировать).
    Если файла нет — возвращает пустой список.
    """
    if not media_config_path.exists():
        return []

    paths = []
    with open(media_config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                paths.append(line)

    return paths
