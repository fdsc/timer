
# Это служебный скрипт
import os

# Список файлов, содержимое которых нужно вывести
files_to_show = [
    "main.py",
    "task_block.py",
#    "notifier.py",
#    "config_manager.py",
#    "date_utils.py",
#    "tasks_storage.py",
    "constants.py"
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
            print(f"[Ошибка при чтении файла: {e}]")
        print(f'Конец файла "{filename}"\n')
    else:
        print(f'Файл "{filename}" не найден в текущей директории.\n')
