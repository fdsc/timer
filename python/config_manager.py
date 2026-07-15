import os
import json
import tkinter as tk
import subprocess
from tkinter import filedialog
from pathlib import Path

CONFIG_STORE_PATH = Path.home() / ".config" / "vinny-task-tracker" / "config_store.json"
MEDIA_CONFIG_PATH = None  # будет установлено после получения data_dir
MEDIA_CONFIG_FILE = "media.conf"
DEFAULT_VOLUME = 100


def get_folder_via_zenity(text, initialDir) -> str | None:
    # zenity --file-selection --directory --filename="$HOME/.config/" --title="Выберите папку для задач"
    try:
        result = subprocess.run(
            ["zenity", "--file-selection", "--directory", f"--title=\"{text}\"", f"--filename=\"initialDir\""],
            capture_output=True,
            text=True,
            check=False  # не выбрасываем исключение при отмене
        )
        path = result.stdout.strip()
        return path if path else None
    except FileNotFoundError:
        return None


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
                    MEDIA_CONFIG_PATH = saved_path / MEDIA_CONFIG_FILE
                    return saved_path
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Диалог выбора папки
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    initial_dir = str(Path.home() / ".config")
    data_dir = get_folder_via_zenity("Выберите папку для хранения задач и настроек", initial_dir)
    root.destroy()

    if not data_dir:
        sys.exit(1)

    data_dir_path = Path(data_dir).expanduser().resolve()
    data_dir_path.mkdir(parents=True, exist_ok=True)

    MEDIA_CONFIG_PATH = data_dir_path / MEDIA_CONFIG_FILE

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

    if "geometry" not in opts:
        opts["geometry"] = "1024x768"

    if "combodefer" not in opts:
        opts["combodefer"] = "0"

    if not opts_path.exists() or "volume_percent" not in opts if opts_path.exists() else True:
        with open(opts_path, "w", encoding="utf-8") as f:
            json.dump(opts, f, ensure_ascii=False, indent=2)

    return opts


def save_opts(data_dir: Path, opts: dict) -> None:
    opts_path = data_dir / "opts.json"
    with open(opts_path, "w", encoding="utf-8") as f:
        json.dump(opts, f, ensure_ascii=False, indent=2)


def init_media_config(data_dir: Path) -> Path:
    """
    Создаёт MEDIA_CONFIG_FILE, если его нет.
    Формат: одна строка — один путь к файлу.
    Строки по порядку:
      1. звук для обычной непросроченной задачи
      2. звук для обычной просроченной задачи
      3. звук для важной непросроченной задачи
      4. звук для важной просроченной задачи
    Если файл уже есть — не перезаписывает, но гарантирует, что он существует.
    Возвращает путь к файлу.
    """
    media_path = data_dir / MEDIA_CONFIG_FILE

    if media_path.exists():
        return media_path

    # Дефолтные пути (можно заменить на любые, которые реально есть в системе)
    defaults = [
        "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
        "/usr/share/sounds/freedesktop/stereo/suspend-error.oga",
        "low_tone.flac",
        "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
    ]

    with open(media_path, "w", encoding="utf-8") as f:
        for line in defaults:
            f.write(line + "\n")

    return media_path


def load_media_paths(media_config_path: Path):
    """
    Загружает пути из MEDIA_CONFIG_FILE.
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
