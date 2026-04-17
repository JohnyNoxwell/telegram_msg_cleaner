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

MAC_CALENDAR_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
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
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
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


def install_macos(python_exe: str, work_dir: str, interval_hours: int = 12, fixed_time: dict = None):
    log_path = os.path.join(work_dir, "LOGS", "autoclean_daemon.log")
    err_path = os.path.join(work_dir, "LOGS", "autoclean_daemon_err.log")

    if fixed_time:
        plist_content = MAC_CALENDAR_PLIST_TEMPLATE.format(
            python_executable=python_exe,
            working_dir=work_dir,
            hour=fixed_time["hour"],
            minute=fixed_time["minute"],
            log_path=log_path,
            err_path=err_path
        )
        mode_desc = f"ежедневно в {fixed_time['hour']:02d}:{fixed_time['minute']:02d}"
    else:
        interval_seconds = interval_hours * 3600
        plist_content = MAC_PLIST_TEMPLATE.format(
            python_executable=python_exe,
            working_dir=work_dir,
            interval_seconds=interval_seconds,
            log_path=log_path,
            err_path=err_path
        )
        mode_desc = f"каждые {interval_hours} ч."

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
        print(f"✅ Демон успешно зарегистрирован ({mode_desc}) и запущен на macOS!")
        print(f"Логи будут писаться в:\n- {log_path}\n- {err_path}")
    else:
        print("⚠️ Ошибка регистрации демона. Ошибка:", res.stderr.decode('utf-8', errors='ignore'))


def install_linux(python_exe: str, work_dir: str, interval_hours: int = 12, fixed_time: dict = None):
    if fixed_time:
        cron_time = f"{fixed_time['minute']} {fixed_time['hour']} * * *"
        mode_desc = f"ежедневно в {fixed_time['hour']:02d}:{fixed_time['minute']:02d}"
    else:
        if interval_hours == 1:
            cron_time = "0 * * * *"
        elif interval_hours < 24:
            cron_time = f"0 */{interval_hours} * * *"
        else:
            days = interval_hours // 24
            cron_time = f"0 0 */{days} * *"
        mode_desc = f"каждые {interval_hours} ч."

    command = f"cd \"{work_dir}\" && {python_exe} -m tg_msg_manager.cli clean --apply --yes >> \"{work_dir}/LOGS/autoclean_daemon.log\" 2>&1"
    cron_job = f"{cron_time} {command}"

    try:
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = res.stdout if res.returncode == 0 else ""

        new_cron_lines = [line for line in current_cron.splitlines() if "tg_msg_manager.cli clean" not in line]
        new_cron_lines.append(cron_job)
        
        cron_input = "\n".join(new_cron_lines) + "\n"
        subprocess.run(["crontab", "-"], input=cron_input, text=True, check=True)
        
        print(f"✅ Задача успешно добавлена в crontab Linux ({mode_desc})!")
        print(f"Расписание: {cron_time}")
        print(f"Логи: {work_dir}/LOGS/autoclean_daemon.log")
    except Exception as e:
        print(f"⚠️ Ошибка настройки cron: {e}")


def install_windows(python_exe: str, work_dir: str, interval_hours: int = 12, fixed_time: dict = None):
    task_name = "TGMsgManager_AutoClean"
    command = f"{python_exe}"
    args = f"-m tg_msg_manager.cli clean --apply --yes"
    full_tr = f"\"{command}\" {args}"

    if fixed_time:
        st_time = f"{fixed_time['hour']:02d}:{fixed_time['minute']:02d}"
        sch_cmd = [
            "schtasks", "/Create", 
            "/SC", "DAILY", 
            "/ST", st_time,
            "/TN", task_name,
            "/TR", full_tr,
            "/F"
        ]
        mode_desc = f"ежедневно в {st_time}"
    else:
        interval_mins = interval_hours * 60
        sch_cmd = [
            "schtasks", "/Create", 
            "/SC", "MINUTE", 
            "/MO", str(interval_mins),
            "/TN", task_name,
            "/TR", full_tr,
            "/F"
        ]
        mode_desc = f"каждые {interval_hours} ч."

    print("Создаю задачу в Планировщике Windows (schtasks)...")
    try:
        res = subprocess.run(sch_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Задача успешно добавлена в Планировщик Windows ({mode_desc})!")
            print(f"Имя задачи: {task_name}")
        else:
            print("⚠️ Ошибка Windows schtasks:")
            print(res.stderr)
    except Exception as e:
        print(f"⚠️ Ошибка вызова schtasks: {e}")


def run_scheduler(config_dir: str):
    print("=== Установка авто-удаления сообщений (Auto-Clean) ===\n")
    
    print("Выберите режим расписания:")
    print(" 1. С интервалом (например, каждые 12 часов)")
    print(" 2. В конкретное время (например, каждый день в 05:00)")
    
    mode = input("Ваш выбор (1 или 2, по умолчанию 1): ").strip()
    
    interval_hours = 12
    fixed_time = None
    
    if mode == "2":
        time_str = input("Введите время в формате ЧЧ:ММ (24-часовой формат, по умолчанию 05:00): ").strip()
        if not time_str:
            time_str = "05:00"
        
        try:
            if ":" not in time_str:
                raise ValueError
            h_str, m_str = time_str.split(":")
            h, m = int(h_str), int(m_str)
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            fixed_time = {"hour": h, "minute": m}
        except ValueError:
            print("Некорректный формат времени. Будет использовано 05:00.")
            fixed_time = {"hour": 5, "minute": 0}
    else:
        ans = input("Введите интервал запуска в часах (по умолчанию 12): ").strip()
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
        install_macos(python_exe, work_dir, interval_hours, fixed_time)
    elif platform.startswith("linux"):
        install_linux(python_exe, work_dir, interval_hours, fixed_time)
    elif platform == "win32":
        install_windows(python_exe, work_dir, interval_hours, fixed_time)
    else:
        print(f"⚠️ Ваша ОС ({platform}) не поддерживается для автоматической установки.")
        print("Вы можете вручную добавить команду в ваш планировщик:")
        if fixed_time:
            time_desc = f"{fixed_time['hour']:02d}:{fixed_time['minute']:02d}"
            print(f"Каждый день в {time_desc}:")
        else:
            print(f"Каждые {interval_hours} ч.:")
        print(f"cd \"{work_dir}\" && {python_exe} -m tg_msg_manager.cli clean --apply --yes")

    print("\nНастройка завершена!")
