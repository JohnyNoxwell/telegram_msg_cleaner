# 📖 Commands Guide / Руководство по командам

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский: Интерактивный режим и CLI

Начиная с версии 4.0, основным способом взаимодействия является **Интерактивное меню**. 

### 🖥️ 1. Интерактивное меню (Основной режим)
Запускается командой `tg` (если установлены алиасы) или `tg-msg-manager` без аргументов из интерактивного терминала.

**Особенности управления:**
*   **Выбор**: Просто нажмите цифру (напр. `1`), нажимать Enter не нужно.
*   **Отмена/Назад**: Нажмите клавишу **ESC** в любой момент.
*   **Выход**: Нажмите `0` в главном меню.

**Разделы меню:**
1.  **Экспорт**: Синхронизация истории с контекстом.
2.  **Обновление**: Инкрементальная докачка всех активных целей.
3.  **Очистка**: Удаление своих сообщений из групп.
4.  **Архив лички**: Текстовый бэкап приватного чата с подготовленными папками под медиа.
5.  **Удалить данные**: Полная очистка локальной БД по конкретному ID.
6.  **Расписание**: Интерактивная настройка `macOS launchd`.
7.  **Настройка**: Установка терминальных алиасов.
8.  **О программе**: Техническая информация.
9.  **Экспорт из БД**: Выгрузка из SQLite в JSON/Text.

---

### ⌨️ 2. CLI Команды (Для автоматизации)
Для использования в скриптах или планировщике доступны прямые команды.

#### `export` — Сбор истории
```bash
tg-msg-manager export --user-id <ID> [--chat-id <ID>] [--flat]
```
*   `--deep`: Явно включить Deep Mode. Поведение по умолчанию.
*   `--flat`: Только сообщения автора, без контекста.
*   `--depth`: Глубина рекурсивного контекста. По умолчанию `2`.
*   `--context-window`: Размер локального окна кандидатов для Deep Mode.
*   `--max-cluster`: Лимит сообщений в одном context cluster.
*   `--json`: После синка собрать итоговый JSONL-файл. Без `--json` итоговый файл будет TXT.
*   `--force-resync`: Начать заново, игнорируя прогресс в БД.
*   `--limit`: Ограничить число обрабатываемых сообщений в рамках одного sync чата.

**Примеры**
```bash
tg-msg-manager export --user-id 123456789 --chat-id 987654321 --depth 3 --json
tg-msg-manager export --user-id 123456789 --chat-id 987654321 --flat
tg-msg-manager export --user-id 123456789 --depth 5 --json
```

#### `update` — Массовое обновление
```bash
tg-msg-manager update
```
Обновляет все цели, используя настройки (depth, window), сохраненные в базе данных.
После прерванного большого экспорта перед первым видимым прогрессом может быть заметная пауза: сервис готовит shared head prefetch для чата.

#### `clean` — Глобальная очистка
```bash
tg-msg-manager clean [--dry-run] [--apply] [--yes]
```
*   По умолчанию команда работает как безопасный dry-run.
*   `--apply`: Включить реальное удаление.
*   `--yes` / `-y`: Подтвердить боевой режим без дополнительного запроса.

**Примеры**
```bash
tg-msg-manager clean --dry-run
tg-msg-manager clean --apply --yes
```

#### `delete` — Полный purge локальных данных
```bash
tg-msg-manager delete --user-id <ID>
```
Удаляет локальные данные цели из SQLite и связанные export-артефакты.

**Пример**
```bash
tg-msg-manager delete --user-id 123456789
```

#### `db-export` — Выгрузка из базы
```bash
tg-msg-manager db-export --user-id <ID> [--json]
```
Без `--json` команда пишет TXT-файл. С `--json` используется компактный AI-friendly JSONL-профиль без полного `raw_payload`.

**Примеры**
```bash
tg-msg-manager db-export --user-id 123456789 --json
tg-msg-manager db-export --user-id 123456789
```

#### `export-pm` — Архив лички
```bash
tg-msg-manager export-pm --user-id <ID>
```
**Пример**
```bash
tg-msg-manager export-pm --user-id 123456789
```

#### `schedule` — Планировщик
```bash
tg-msg-manager schedule
```
Интерактивная настройка фонового `update` через `macOS launchd`.

#### `setup` — Установка алиасов
```bash
tg-msg-manager setup
```
Устанавливает алиасы `tg`, `tgr`, `tgd`, `tge`, `tgu`, `tgpm`.

---

<a id="english"></a>
## 🇬🇧 English: Interactive Mode & CLI

Since Version 4.0, the **Interactive Menu** is the recommended way to operate.

### 🖥️ 1. Interactive Menu (Primary Mode)
Launch via the `tg` shortcut or run `tg-msg-manager` without arguments from an interactive terminal.

**Navigation:**
*   **Selection**: Press any numeric key (e.g., `1`) for instant activation. No Enter key is needed.
*   **Cancel/Back**: Press the **ESC** key at any point to return to the previous screen.
*   **Exit**: Press `0` from the main menu.

**Menu Map:**
1.  **Export History**: Sync message history with conversation context.
2.  **Universal Update**: Incremental sync for all tracked targets.
3.  **Global Cleanup**: Bulk removal of your messages from groups.
4.  **PM Archive**: Text backup of direct messages with prepared media folders.
5.  **Purge Data**: Irreversible removal of a target's history from local storage.
6.  **Scheduler**: Interactive `macOS launchd` setup.
7.  **Setup**: Install terminal aliases.
8.  **About**: System information and versions.
9.  **DB Export Service**: Convert SQLite records to JSON/Text.

---

### ⌨️ 2. CLI Subcommands (For Automation)
Direct commands are available for scripting, Cron, or advanced usage.

#### `export` — History Synchronization
```bash
tg-msg-manager export --user-id <ID> [--chat-id <ID>] [--flat]
```
*   `--deep`: Explicitly enable Deep Mode. This is the default behavior.
*   `--flat`: Fetch only author messages, skipping surrounding context.
*   `--depth`: Recursive context depth. Defaults to `2`.
*   `--context-window`: Candidate window size for Deep Mode.
*   `--max-cluster`: Maximum messages inside one context cluster.
*   `--json`: Write a final JSONL snapshot after sync. Without `--json`, the final export is TXT.
*   `--force-resync`: Restart the sync from the beginning.
*   `--limit`: Cap the number of processed messages inside a single chat sync.

**Examples**
```bash
tg-msg-manager export --user-id 123456789 --chat-id 987654321 --depth 3 --json
tg-msg-manager export --user-id 123456789 --chat-id 987654321 --flat
tg-msg-manager export --user-id 123456789 --depth 5 --json
```

#### `update` — Batch Updater
```bash
tg-msg-manager update
```
The "Smart Sync" engine. It automatically finds all targets in the DB and brings them up to date.
After a large interrupted export, there may be a noticeable pause before the first visible per-target progress while the service prepares a shared head prefetch slice for the chat.

#### `clean` — Global Cleanup
```bash
tg-msg-manager clean [--dry-run] [--apply] [--yes]
```
*   The command is safe by default and runs as dry-run unless `--apply` is provided.
*   `--apply`: Enable real deletion.
*   `--yes` / `-y`: Confirm apply mode without an extra prompt.

**Examples**
```bash
tg-msg-manager clean --dry-run
tg-msg-manager clean --apply --yes
```

#### `delete` — Local Data Purge
```bash
tg-msg-manager delete --user-id <ID>
```
Removes the target's local SQLite state and related export artifacts.

**Example**
```bash
tg-msg-manager delete --user-id 123456789
```

#### `db-export` — Local Data Retrieval
```bash
tg-msg-manager db-export --user-id <ID> [--json]
```
Without `--json`, the command writes TXT. With `--json`, it writes the compact AI-friendly JSONL profile without the full `raw_payload`.

**Examples**
```bash
tg-msg-manager db-export --user-id 123456789 --json
tg-msg-manager db-export --user-id 123456789
```

#### `export-pm` — Private Chat Archive
```bash
tg-msg-manager export-pm --user-id <ID>
```
**Example**
```bash
tg-msg-manager export-pm --user-id 123456789
```

#### `schedule` — Scheduler
```bash
tg-msg-manager schedule
```
Interactive background `update` setup for `macOS launchd`.

#### `setup` — Alias Installer
```bash
tg-msg-manager setup
```
Installs the `tg`, `tgr`, `tgd`, `tge`, `tgu`, and `tgpm` shortcuts.

---

## 🔎 Verification / Проверка

```bash
pip install -e .[dev]
make lint
make format-check
make test
make verify
```

Live smoke-check:

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat --limit 1
```
