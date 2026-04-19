import os
import re
import shutil

def cleanup_exports(export_dir: str):
    if not os.path.exists(export_dir):
        print(f"Директория {export_dir} не найдена.")
        return

    legacy_dir = os.path.join(export_dir, "LEGACY_ARCHIVE")
    os.makedirs(legacy_dir, exist_ok=True)

    files = os.listdir(export_dir)
    
    # 1. Группируем файлы по ID пользователя
    # Паттерн: Экспорт_Имя_ID[_DEEP][_partN].ext
    user_files = {} # uid -> [filenames]
    
    for fn in files:
        if fn == "LEGACY_ARCHIVE" or fn == "changelog.txt":
            continue
            
        # Ищем ID (цифры в конце перед расширением или перед _DEEP)
        m = re.search(r'_(\d+)(_DEEP)?(_part\d+)?\.(txt|jsonl)$', fn)
        if m:
            uid = int(m.group(1))
            if uid not in user_files:
                user_files[uid] = []
            user_files[uid].append(fn)

    print(f"Найдено пользователей: {len(user_files)}")
    
    moved_count = 0
    for uid, fns in user_files.items():
        # Проверяем, есть ли у пользователя и .jsonl и .txt
        has_jsonl = any(f.endswith(".jsonl") for f in fns)
        has_txt = any(f.endswith(".txt") for f in fns)
        
        if has_jsonl and has_txt:
            # Переносим все .txt этого пользователя в архив
            for f in fns:
                if f.endswith(".txt"):
                    old_path = os.path.join(export_dir, f)
                    new_path = os.path.join(legacy_dir, f)
                    shutil.move(old_path, new_path)
                    moved_count += 1
        elif has_txt:
            # Если только .txt, пока не трогаем или тоже в архив?
            # Пользователь просил "причесать", оставим только современные форматы.
            # Но для безопасности перенесем в архив, а не удалим.
            pass

    print(f"Перенесено в {legacy_dir}: {moved_count} файлов.")
    
    # 2. Удаляем пустые папки (если есть)
    for fn in files:
        path = os.path.join(export_dir, fn)
        if os.path.isdir(path) and fn != "LEGACY_ARCHIVE" and not os.listdir(path):
            os.rmdir(path)
            print(f"Удалена пустая папка: {fn}")

if __name__ == "__main__":
    cleanup_exports("PUBLIC_GROUPS")
