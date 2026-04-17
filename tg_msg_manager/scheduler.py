import os
import sys
import json
import subprocess
from pathlib import Path
from .core import _config_path, DEFAULT_CONFIG_CANDIDATES

MAC_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tgmsgmanager.autoclean</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_executable}</string>
        <string>-m</string>
        <string>tg_msg_manager.cli</string>
        <string>clean</string>
        <string>--apply</string>
        <string>--yes</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{err_path}</string>
</dict>
</plist>
"""

def update_config_exclusions(config_dir: str):
    config_path = _config_path(config_dir)
    if not os.path.exists(config_path):
        print(f"Конфигурационный файл {config_path} не найден. Сначала запустите утилиту или скопируйте config.example.json.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            print("Ошибка чтения конфигурации (невалидный JSON). Вопрос про исключения пропущен.")
            return

    print("\n=== Настройка исключений ===")
    print("Вызовы авто-очистки могут обходить важные чаты (Blacklist).")
    print("В файле конфигурации уже есть параметр 'exclude_chats'.")
    ans = input("Хотите дополнить список исключаемых ID чатов (через запятую)? Оставьте пустым, чтобы не менять: ").strip()
    
    if ans:
        new_ids = []
        for x in ans.split(","):
            x = x.strip()
            if x.lstrip('-').isdigit():
                new_ids.append(int(x))
            else:
                print(f"Пропущено '{x}' - не является числовым ID.")
        
        if new_ids:
            existing = config_data.get("exclude_chats", [])
            if existing is None:
                existing = []
            
            # Combine without duplicates
            combined = list(set(existing + new_ids))
            config_data["exclude_chats"] = combined

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            print(f"Конфиг обновлен! В 'exclude_chats' добавлено {len(new_ids)} новых ID.")
        else:
            print("Новые ID не были добавлены.")
    else:
        print("Конфиг оставлен без изменений.")


def install_macos(python_exe: str, work_dir: str, interval_hours: int):
    interval_seconds = interval_hours * 3600
    log_path = os.path.join(work_dir, "LOGS", "autoclean_daemon.log")
    err_path = os.path.join(work_dir, "LOGS", "autoclean_daemon_err.log")

    plist_content = MAC_PLIST_TEMPLATE.format(
        python_executable=python_exe,
        working_dir=work_dir,
        interval_seconds=interval_seconds,
        log_path=log_path,
        err_path=err_path
    )

    plist_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(plist_dir, exist_ok=True)
    plist_path = os.path.join(plist_dir, "com.tgmsgmanager.autoclean.plist")

    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)

    print(f"Конфигурация Launchd создана: {plist_path}")
    
    # Reload daemon
    subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
    res = subprocess.run(["launchctl", "load", plist_path], capture_output=True)
    
    if res.returncode == 0:
        print("✅ Демон успешно зарегистрирован и запущен на macOS!")
        print(f"Логи будут писаться в:\n- {log_path}\n- {err_path}")
    else:
        print("⚠️ Ошибка регистрации демона. Ошибка:", res.stderr.decode('utf-8', errors='ignore'))


def install_linux(python_exe: str, work_dir: str, interval_hours: int):
    # Генерация cron строки
    # каждые N часов (0 */N * * *)
    if interval_hours == 1:
        cron_time = "0 * * * *"
    elif interval_hours < 24:
        cron_time = f"0 */{interval_hours} * * *"
    else:
        days = interval_hours // 24
        cron_time = f"0 0 */{days} * *"

    command = f"cd \"{work_dir}\" && {python_exe} -m tg_msg_manager.cli clean --apply --yes >> \"{work_dir}/LOGS/autoclean_daemon.log\" 2>&1"
    cron_job = f"{cron_time} {command}"

    try:
        # Получаем текущий crontab (может вернуть ошибку 1, если cron пуст)
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = res.stdout if res.returncode == 0 else ""

        # Убираем старую задачу, если есть
        new_cron_lines = [line for line in current_cron.splitlines() if "tg_msg_manager.cli clean" not in line]
        new_cron_lines.append(cron_job)
        
        # Добавляем в crontab
        cron_input = "\n".join(new_cron_lines) + "\n"
        subprocess.run(["crontab", "-"], input=cron_input, text=True, check=True)
        
        print("✅ Задача успешно добавлена в crontab Linux!")
        print(f"Расписание: {cron_time}")
        print(f"Логи: {work_dir}/LOGS/autoclean_daemon.log")
    except Exception as e:
        print(f"⚠️ Ошибка настройки cron: {e}")


def install_windows(python_exe: str, work_dir: str, interval_hours: int):
    interval_mins = interval_hours * 60
    task_name = "TGMsgManager_AutoClean"
    
    # Команда, которая не открывает терминал (через pythonw, если возможно, но используем текущий sys.executable)
    # Для Windows лучше запускать из .bat или просто аргументом
    command = f"{python_exe}"
    args = f"-m tg_msg_manager.cli clean --apply --yes"

    print("Создаю задачу в Планировщике Windows (schtasks)...")
    try:
        # Для schtasks мы указываем /TR как исполняемый вызов
        full_tr = f"\"{command}\" {args}"
        
        # schtasks /Create /SC MINUTE /MO 60 /TN TGMsgManager_AutoClean /TR "..." 
        # /F - перезаписать если есть
        sch_cmd = [
            "schtasks", "/Create", 
            "/SC", "MINUTE", 
            "/MO", str(interval_mins),
            "/TN", task_name,
            "/TR", full_tr,
            "/F"
        ]
        
        res = subprocess.run(sch_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ Задача успешно добавлена в Планировщик Windows!")
            print(f"Имя задачи: {task_name}")
            print("Она будет исполняться в фоновом режиме.")
        else:
            print("⚠️ Ошибка Windows schtasks:")
            print(res.stderr)
    except Exception as e:
        print(f"⚠️ Ошибка вызова schtasks: {e}")


def run_scheduler(config_dir: str):
    print("=== Установка авто-удаления сообщений (Auto-Clean) ===")
    
    # 1. Интервал
    ans = input("Введите интервал запуска в часах (по умолчанию 12): ").strip()
    interval_hours = 12
    if ans:
        if ans.isdigit() and int(ans) > 0:
            interval_hours = int(ans)
        else:
            print("Некорректный ввод. Установлено по умолчанию: 12.")

    # 2. Исключения (обновление config_dir)
    update_config_exclusions(config_dir)

    # 3. Установка демона
    python_exe = sys.executable
    work_dir = os.path.abspath(config_dir)
    platform = sys.platform

    print(f"\nРегистрация демона на платформе: {platform}")
    if platform == "darwin":
        install_macos(python_exe, work_dir, interval_hours)
    elif platform.startswith("linux"):
        install_linux(python_exe, work_dir, interval_hours)
    elif platform == "win32":
        install_windows(python_exe, work_dir, interval_hours)
    else:
        print(f"⚠️ Ваша ОС ({platform}) не поддерживается для автоматической установки.")
        print("Вы можете вручную добавить команду в ваш планировщик:")
        print(f"cd \"{work_dir}\" && {python_exe} -m tg_msg_manager.cli clean --apply --yes")

    print("\nНастройка завершена!")
