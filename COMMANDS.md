# 📖 Commands Guide / Руководство по командам

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский: Интерактивный режим и CLI

Начиная с версии 4.0, основным способом взаимодействия является **Интерактивное меню**. 

### 🖥️ 1. Интерактивное меню (Основной режим)
Запускается командой `tg` (если установлены алиасы) или `tg-msg-manager` без аргументов.

**Особенности управления:**
*   **Выбор**: Просто нажмите цифру (напр. `1`), нажимать Enter не нужно.
*   **Отмена/Назад**: Нажмите клавишу **ESC** в любой момент.
*   **Выход**: Нажмите `0` в главном меню.

**Разделы меню:**
1.  **Экспорт**: Синхронизация истории с контекстом.
2.  **Обновление**: Инкрементальная докачка всех активных целей.
3.  **Очистка**: Удаление своих сообщений из групп.
4.  **Личка + Медиа**: Полный бэкап приватного чата (текст + файлы).
5.  **Удалить данные**: Полная очистка локальной БД по конкретному ID.
6.  **О программе**: Техническая информация.
7.  **Экспорт из БД**: Выгрузка из SQLite в JSON/Text.

---

### ⌨️ 2. CLI Команды (Для автоматизации)
Для использования в скриптах или планировщике доступны прямые команды.

#### `export` — Сбор истории
```bash
tg-msg-manager export --user-id <ID> [--chat-id <ID>] [--flat]
```
*   `--flat`: Только сообщения автора, без контекста.
*   `--force-resync`: Начать заново, игнорируя прогресс в БД.

#### `update` — Массовое обновление
```bash
tg-msg-manager update [--force-resync]
```
Обновляет все цели, используя настройки (depth, window), сохраненные в базе данных.

#### `db-export` — Выгрузка из базы (New!)
```bash
tg-msg-manager db-export --user-id <ID> [--json]
```
Экспортирует сохраненные сообщения в файл.

---

<a id="english"></a>
## 🇬🇧 English: Interactive Mode & CLI

Since Version 4.0, the **Interactive Menu** is the recommended way to operate.

### 🖥️ 1. Interactive Menu (Primary Mode)
Launch via the `tg` shortcut or run `tg-msg-manager` without arguments.

**Navigation:**
*   **Selection**: Press any numeric key (e.g., `1`) for instant activation. No Enter key is needed.
*   **Cancel/Back**: Press the **ESC** key at any point to return to the previous screen.
*   **Exit**: Press `0` from the main menu.

**Menu Map:**
1.  **Export History**: Sync message history with conversation context.
2.  **Universal Update**: Incremental sync for all tracked targets.
3.  **Global Cleanup**: Bulk removal of your messages from groups.
4.  **PM Media Archive**: Total backup of direct messages with photos/files.
5.  **Purge Data**: Irreversible removal of a target's history from local storage.
6.  **About**: System information and versions.
7.  **DB Export Service**: Convert SQLite records to JSON/Text.

---

### ⌨️ 2. CLI Subcommands (For Automation)
Direct commands are available for scripting, Cron, or advanced usage.

#### `export` — History Synchronization
```bash
tg-msg-manager export --user-id <ID> [--chat-id <ID>] [--flat]
```
*   `--flat`: Fetch only author messages, skipping surrounding context.
*   `--force-resync`: Restart the sync from the beginning.

#### `update` — Batch Updater
```bash
tg-msg-manager update
```
The "Smart Sync" engine. It automatically finds all targets in the DB and brings them up to date.

#### `db-export` — Local Data Retrieval
```bash
tg-msg-manager db-export --user-id <ID> [--json]
```
Converts the internal SQLite representation into human-readable files.
