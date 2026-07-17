# Это служебный скрипт
# python3 printtxt.py > /inRamA/txt.txt
import os

# Список файлов, содержимое которых нужно вывести
files_to_show = [
    "main.py",
    "task_block.py",
]


#files_to_show.append("app_singletone.py")
#files_to_show.append("main_gui_check_control_tasks.py")
#files_to_show.append("config_manager.py")
#files_to_show.append("constants.py")
files_to_show.append("date_utils.py")
#files_to_show.append("main_gui_audio_control.py")
#files_to_show.append("main_gui_helper.py")
files_to_show.append("main_gui_input_panel.py")
#files_to_show.append("main_gui_resize_handler.py")
#files_to_show.append("main_gui_tabs_layout.py")
#files_to_show.append("main_gui_task_frames_sorting_logic.py")
#files_to_show.append("main_gui_window.py")
#files_to_show.append("main_load_config_path.py")
#files_to_show.append("notifier.py")
#files_to_show.append("task_block_gui_delete_confirmation_mixin.py")
#files_to_show.append("task_block_gui_layout.py")
#files_to_show.append("task_block_gui_priority_colors.py")
#files_to_show.append("task_block_tasks.py")
#files_to_show.append("task_block_timer_and_alert.py")
#files_to_show.append("tasks_storage.py")


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
