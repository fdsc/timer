# Это служебный скрипт
import os

# Список файлов, содержимое которых нужно вывести
files_to_show = [
#    "app_singletone.py",
    "config_manager.py",
#    "constants.py",
    "date_utils.py",
#    "main_gui_audio_control.py",
#    "main_gui_helper.py",
#    "main_gui_input_panel.py",
#    "main_gui_resize_handler.py",
#    "main_gui_tabs_layout.py",
#    "main_gui_task_frames_sorting_logic.py",
#    "main_gui_window.py",
#    "main_load_config_path.py",
    "main.py",
#    "notifier.py",
#    "task_block_gui_delete_confirmation_mixin.py",
#    "task_block_gui_layout.py",
#    "task_block_gui_priority_colors.py",
    "task_block.py",
    "task_block_tasks.py",
#    "task_block_timer_and_alert.py",
#    "tasks_storage.py"
]

current_dir = os.getcwd()

for filename in files_to_show:
    filepath = os.path.join(current_dir, filename)

    # Проверяем, существует ли файл и является ли он обычным файлом
    if os.path.isfile(filepath):
        print(f"**{filename}**")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                print(content)
        except UnicodeDecodeError:
            # Если файл не текстовый (например, бинарный), пробуем прочитать как байты
            with open(filepath, "rb") as f:
                content = f.read()
                print("[Бинарный файл — вывод в виде байтов]")
                print(content)
        except Exception as e:
            print(f"ERROR: [Ошибка при чтении файла: {e}]")
        print(f'Конец файла "{filename}"\n')
    else:
        print(f'ERROR: Файл "{filename}" не найден в текущей директории.\n')
