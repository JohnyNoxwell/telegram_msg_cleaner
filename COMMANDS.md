# 📖 Commands Guide / Руководство по командам

Утилита запускается командой `tg-message-cleaner` и поддерживает три мощных режима работы.
The utility is executed via `tg-message-cleaner` supporting three powerful subcommands.

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---
<a id="русский"></a>
## 🇷🇺 Русский: Подробное руководство

### 🧹 1. Режим очистки (`clean`) — *По умолчанию*
Удаляет ваши сообщения из доступных групп и каналов. Тонкая настройка (исключения, даты) производится в файле конфигурации.

**Флаги и Аргументы:**
* `--dry-run` (или `--dry-run-flag`) — 🛡️ **Безопасный режим.** Скрипт просканирует чаты и покажет точное количество сообщений, но ничего **не удалит**.
* `--apply` — 🧨 **Боевой режим.** Принудительное реальное удаление сообщений (игнорирует параметр `dry_run` в конфиге).
* `--yes` — 🤖 Пропуск подтверждения. Идеально для автоматизации скриптов (cron), чтобы утилита не просила нажать `[y/N]`.

**Примеры использования:**
```bash
tg-message-cleaner clean --dry-run
tg-message-cleaner clean --apply --yes

# Альтернативный запуск напрямую (python -m):
python -m tg_message_cleaner.cli clean --dry-run
```

### 📥 2. Режим экспорта (`export`)
Ищет все сообщения заданного пользователя и выкачивает их в удобный для чтения текстовый файл, сохраняя хронологию и вложенные ответы (replies). Поиск выполняется **в 10 потоков**, обеспечивая сверхбыструю выгрузку в папку `EXPORTED_USRS`.

**Флаги и Аргументы:**
* `--user-id` *(Обязательный)* — ID или username (ник) целевого пользователя.
* `--chat-id` *(Опциональный)* — ID или username конкретной группы для поиска. Если не указать — скрипт проверит **абсолютно все** ваши чаты.
* `--out` *(Опциональный)* — Свое имя текстового файла вместо сгенерированного автоматически `Экспорт_Имя_ID.txt`.

**Примеры использования:**
```bash
# Глобальный сканер по всем вашим чатам
tg-message-cleaner export --user-id 5378570247

# Точечный сканер внутри одной конкретной группы
tg-message-cleaner export --user-id "spammer22" --chat-id -100123456789
```

### 🔄 3. Режим обновления (`update`)
Магическая команда. Автоматически сканирует вашу папку `EXPORTED_USRS` и **параллельно** загружает *новые* сообщения для **каждого** ранее выгруженного пользователя. Автоматически фиксирует смену никнеймов и записывает краткий отчет проделанной работы в `changelog.txt`.

**Пример использования:**
```bash
tg-message-cleaner update
```

### 🌍 4. Глобальные Флаги
**`--config-dir`** — Задает путь к папке с вашим конфигурационным файлом. 
```bash
tg-message-cleaner --config-dir /etc/tg_cleaner export --user-id 12345
```

---
<a id="english"></a>
## 🇬🇧 English: Extensive Guide

### 🧹 1. Clean Mode (`clean`) — *Default*
Deletes your messages from accessible groups and channels. Fine-tuning filters and blacklists are handled via your config file.

**Flags & Arguments:**
* `--dry-run` — 🛡️ **Safe rehearsal.** Audits your chats and prints stats on what would be removed, but performs **no actual deletion**.
* `--apply` — 🧨 **Combat mode.** Real deletion. Forcefully overrides the `dry_run` configuration.
* `--yes` — 🤖 Bypasses the initial `[y/N]` confirmation prompts. Highly useful for headless cron jobs.

**Examples:**
```bash
tg-message-cleaner clean --dry-run
tg-message-cleaner clean --apply --yes

# Run directly via python module:
python -m tg_message_cleaner.cli clean --dry-run
```

### 📥 2. Export Mode (`export`)
Locates a target user's entire footprint and extracts their messages into elegantly formatted text files, complete with chronological order and embedded replies. Lookups are executed with a **concurrency pool of 10** for ultra-fast speeds, saving all data to an auto-created `EXPORTED_USRS` folder.

**Flags & Arguments:**
* `--user-id` *(Required)* — The numeric ID or username of the targeted entity.
* `--chat-id` *(Optional)* — Restrict scanning to a specific chat ID/username. If omitted, performs a **global parallel scan across all your chats**.
* `--out` *(Optional)* — A custom filename for the output.

**Examples:**
```bash
# Global parallel scan across all your joined communities
tg-message-cleaner export --user-id 5378570247

# Targeted extraction in a designated group
tg-message-cleaner export --user-id "spammer22" --chat-id -100123456789
```

### 🔄 3. Update Mode (`update`)
A magic bullet command. It automatically reads your `EXPORTED_USRS` cache and performs a **highly concurrent** fetch of only the *newest* messages for every previously extracted user. It also dynamically tracks nickname changes into the document headers and generates a `changelog.txt` summary file upon completion.

**Examples:**
```bash
tg-message-cleaner update
```

### 🌍 4. Global Flags
**`--config-dir`** — Instructs the tool to fetch its configuration from a specific directory path.
```bash
tg-message-cleaner --config-dir /etc/tg_cleaner clean --apply --yes
```
