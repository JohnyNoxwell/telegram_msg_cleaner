import os
import sys
from pathlib import Path


ALIASES_BLOCK_START = "# >>> tg-msg-manager aliases >>>"
ALIASES_BLOCK_END = "# <<< tg-msg-manager aliases <<<"

ALIAS_TEMPLATE = """{block_start}
alias tgr='cd "{work_dir}" && {python} -m tg_msg_manager.cli clean --dry-run --yes'
alias tgd='cd "{work_dir}" && {python} -m tg_msg_manager.cli clean --apply --yes'
alias tge='cd "{work_dir}" && {python} -m tg_msg_manager.cli export --user-id'
alias tgu='cd "{work_dir}" && {python} -m tg_msg_manager.cli update'
alias tgpm='cd "{work_dir}" && {python} -m tg_msg_manager.cli export-pm --user-id'
alias tg='echo "
  tg-msg-manager shortcuts:
  ─────────────────────────────────────
  tgr   — 🛡️  Репетиция удаления (dry-run)
  tgd   — 🧨  Боевое удаление сообщений
  tge   — 📥  Экспорт сообщений из групп (+ user ID)
  tgu   — 🔄  Обновить все экспорты
  tgpm  — 💬  Архив личной переписки с медиа (+ user ID)
  ─────────────────────────────────────
"'
{block_end}
"""

# Windows: создаём .bat-файлы в папке проекта и добавляем её в PATH через PowerShell профиль
WIN_BAT_COMMANDS = {
    "tgr": 'clean --dry-run --yes',
    "tgd": 'clean --apply --yes',
    "tge": 'export --user-id',
    "tgu": 'update',
    "tgpm": 'export-pm --user-id',
}

WIN_BAT_TEMPLATE = '@echo off\ncd /d "{work_dir}"\n"{python}" -m tg_msg_manager.cli {args} %*\n'

WIN_HELP_BAT = """@echo off
echo.
echo   tg-msg-manager shortcuts:
echo   ─────────────────────────────────────
echo   tgr   — Репетиция удаления (dry-run)
echo   tgd   — Боевое удаление сообщений
echo   tge   — Экспорт сообщений из групп (+ user ID)
echo   tgu   — Обновить все экспорты
echo   tgpm  — Архив личной переписки с медиа (+ user ID)
echo   ─────────────────────────────────────
echo.
"""


def _detect_shell_rc() -> str:
    """Определяет файл конфигурации шелла пользователя."""
    shell = os.environ.get("SHELL", "")
    home = str(Path.home())

    if "zsh" in shell:
        return os.path.join(home, ".zshrc")
    elif "bash" in shell:
        # На macOS Catalina+ по умолчанию zsh, но некоторые используют bash
        bashrc = os.path.join(home, ".bashrc")
        bash_profile = os.path.join(home, ".bash_profile")
        # .bash_profile приоритетнее на macOS
        if sys.platform == "darwin" and os.path.exists(bash_profile):
            return bash_profile
        return bashrc
    elif "fish" in shell:
        return os.path.join(home, ".config", "fish", "config.fish")
    
    # Фолбэк
    zshrc = os.path.join(home, ".zshrc")
    bashrc = os.path.join(home, ".bashrc")
    if os.path.exists(zshrc):
        return zshrc
    return bashrc


def _remove_old_aliases(content: str) -> str:
    """Удаляет старый блок алиасов, если он уже был вставлен ранее."""
    start = content.find(ALIASES_BLOCK_START)
    end = content.find(ALIASES_BLOCK_END)
    if start != -1 and end != -1:
        end += len(ALIASES_BLOCK_END)
        # Убираем перевод строки после блока
        if end < len(content) and content[end] == '\n':
            end += 1
        content = content[:start] + content[end:]
    return content


def setup_unix(work_dir: str, python_exe: str):
    """Прописывает алиасы в .zshrc / .bashrc."""
    rc_path = _detect_shell_rc()

    alias_block = ALIAS_TEMPLATE.format(
        block_start=ALIASES_BLOCK_START,
        block_end=ALIASES_BLOCK_END,
        work_dir=work_dir,
        python=python_exe,
    )

    # Читаем текущее содержимое
    existing = ""
    if os.path.exists(rc_path):
        with open(rc_path, "r", encoding="utf-8") as f:
            existing = f.read()

    # Удаляем старый блок (если переустановка)
    cleaned = _remove_old_aliases(existing)

    # Дописываем новый блок
    with open(rc_path, "w", encoding="utf-8") as f:
        f.write(cleaned.rstrip("\n") + "\n\n" + alias_block)

    print(f"✅ Алиасы успешно добавлены в: {rc_path}")
    print(f"   Для активации выполните: source {rc_path}")
    print(f"   Или просто откройте новый терминал.")


def setup_windows(work_dir: str, python_exe: str):
    """Создаёт .bat-файлы в папке проекта для быстрого вызова команд."""
    bat_dir = os.path.join(work_dir, "shortcuts")
    os.makedirs(bat_dir, exist_ok=True)

    for name, args in WIN_BAT_COMMANDS.items():
        bat_path = os.path.join(bat_dir, f"{name}.bat")
        content = WIN_BAT_TEMPLATE.format(
            work_dir=work_dir,
            python=python_exe,
            args=args,
        )
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Справочный файл tg.bat
    tg_bat = os.path.join(bat_dir, "tg.bat")
    with open(tg_bat, "w", encoding="utf-8") as f:
        f.write(WIN_HELP_BAT)

    print(f"✅ Ярлыки (.bat) созданы в папке: {bat_dir}")
    print(f"   Добавьте эту папку в системную переменную PATH,")
    print(f"   чтобы использовать команды tgr, tgd, tge, tgu, tgpm из любого места.")


def run_setup(config_dir: str):
    work_dir = os.path.abspath(config_dir)
    python_exe = sys.executable

    print("=== Установка быстрых алиасов tg-msg-manager ===\n")
    print(f"📂 Рабочая директория: {work_dir}")
    print(f"🐍 Python: {python_exe}\n")

    if sys.platform in ("darwin", "linux") or sys.platform.startswith("linux"):
        setup_unix(work_dir, python_exe)
    elif sys.platform == "win32":
        setup_windows(work_dir, python_exe)
    else:
        print(f"⚠️  Платформа {sys.platform} не поддерживается для автоустановки алиасов.")
        return

    print(f"""
  Доступные команды:
  ─────────────────────────────────────
  tgr   — 🛡️  Репетиция удаления (dry-run)
  tgd   — 🧨  Боевое удаление сообщений
  tge   — 📥  Экспорт сообщений из групп (+ user ID)
  tgu   — 🔄  Обновить все экспорты
  tgpm  — 💬  Архив личной переписки с медиа (+ user ID)
  tg    — 📖  Показать эту справку
  ─────────────────────────────────────
""")
