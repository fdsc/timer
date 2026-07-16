import os

def rename_files_with_hyphen():
    """
    Переименовывает все файлы в текущей директории, содержащие дефис,
    заменяя дефис на подчёркивание. Файлы без дефиса не трогаются.
    """
    current_dir = os.getcwd()
    print(f"Рабочая директория: {current_dir}")

    for filename in os.listdir(current_dir):
        # Полный путь к файлу
        filepath = os.path.join(current_dir, filename)

        # Обрабатываем только файлы (не папки)
        if not os.path.isfile(filepath):
            continue

        # Проверяем, есть ли дефис в имени
        if '-' not in filename:
            continue

        # Формируем новое имя
        new_filename = filename.replace('-', '_')

        # Если имя не изменилось (на всякий случай) — пропускаем
        if new_filename == filename:
            continue

        new_filepath = os.path.join(current_dir, new_filename)

        # Проверяем, не занято ли уже новое имя
        if os.path.exists(new_filepath):
            print(f"ОШИБКА: '{new_filename}' уже существует, пропускаю '{filename}'")
            continue

        # Переименование
        os.rename(filepath, new_filepath)
        print(f"Переименован: '{filename}' -> '{new_filename}'")

if __name__ == "__main__":
    rename_files_with_hyphen()

