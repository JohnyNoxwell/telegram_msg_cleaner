# 📖 Commands Guide / Руководство по командам

Утилита запускается командой `tg-msg-manager` и поддерживает три мощных режима работы.
The utility is executed via `tg-msg-manager` supporting three powerful subcommands.

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
tg-msg-manager clean --dry-run
tg-msg-manager clean --apply --yes

# Альтернативный запуск напрямую (python -m):
python -m tg_msg_manager.cli clean --dry-run
```

### 📥 2. Режим экспорта (`export`)
Ищет все сообщения заданного пользователя и выкачивает их в удобный для чтения текстовый файл, сохраняя хронологию и вложенные ответы (replies). Поиск выполняется **в 10 потоков**, обеспечивая сверхбыструю выгрузку в папку `PUBLIC_GROUPS`.

**Флаги и Аргументы:**
* `--user-id` *(Обязательный)* — ID или username целевого пользователя.
* `--chat-id` *(Опциональный)* — ID или username конкретной группы для поиска. Если не указать — скрипт проверит **все** ваши чаты.
* `--out` *(Опциональный)* — Свое имя файла.
* `--json` — 📦 Экспорт в формате **JSONL** (одна строка — один JSON-объект). Рекомендуется для дальнейшего анализа.
* `--deep` — 🧬 **Deep Search Mode.** Включает поиск контекста. Скрипт найдет сообщения цели и "притянет" к ним реплики и соседние сообщения.

**Настройка Deep Mode (тонкая наладка):**
* `--context-window` — Размер окна контекста (0 — только сообщения цели, 1+ — искать вокруг).
* `--time-threshold` — Порог связи (сек). Если сообщения идут с таким разрывом, они считаются связанными (дефолт: 120).
* `--max-cluster` — Ограничение количества сообщений в одном фрагменте контекста (дефолт: 15).

**Примеры использования:**
```bash
# Обычный текстовый экспорт по всем чатам
tg-msg-manager export --user-id 1234567

# Глубокий экспорт в JSONL из конкретной группы
tg-msg-manager export --user-id "spammer" --chat-id -100123 --json --deep
```

### 🔄 3. Режим обновления (`update`)
Магическая команда. Автоматически сканирует `PUBLIC_GROUPS` и докачивает новые сообщения. Скрипт сам понимает, какой файл был в JSONL, а какой в TXT, и кто был выгружен в режиме DEEP.

**Флаги:**
* `--json` — Обновлять только файлы `.jsonl`.
* `--deep` — Обновлять в режиме глубокого поиска контекста.

**Пример использования:**
```bash
tg-msg-manager update
```

### 💬 4. Экспорт личной переписки (`export-pm`)
Полный архив приватного диалога: текст + **все медиафайлы** (фото, видео, кружки, голосовые, GIF, документы). Медиа автоматически раскладываются по категориям в отдельные папки внутри `PRIVAT_DIALOGS/Имя_@юзернейм_ID/media/`.

> ⚙️ **Встроенные защиты:** Инкрементальное обновление (докачивает только новое), лимит 50 МБ на файл, умный балансировщик загрузок (эмуляция обычного пользователя).

**Флаги и Аргументы:**
* `--user-id` *(Обязательный)* — ID или username пользователя, чей приватный диалог нужно архивировать.

**Примеры использования:**
```bash
tg-msg-manager export-pm --user-id 5378570247
tg-msg-manager export-pm --user-id "johndoe"
```

**Структура выгрузки:**
```
PRIVAT_DIALOGS/
└── John Doe_@johndoe_+79991234567_5378570247/
    ├── chat_log.txt
    └── media/
        ├── photos/
        ├── videos/
        ├── video_notes/
        ├── voices/
        ├── gifs/
        └── documents/
```

### ⏳ 5. Режим авто-очистки (`schedule`)
Новейший механизм "таймера самоуничтожения". Единожды задав вопросы через консоль (выбор режима: **интервал** или **точное время**, исключения), утилита сама зарегистрирует себя системным фоновым демоном (через `launchd` на macOS, `cron` на Linux или Планировщик задач на Windows). Ваши сообщения будут стабильно удаляться полностью в фоновом режиме по расписанию!

**Пример использования:**
```bash
tg-msg-manager schedule
```

### 🌍 6. Глобальные Флаги
**`--config-dir`** — Задает путь к папке с вашим конфигурационным файлом. 
```bash
tg-msg-manager --config-dir /etc/tg_cleaner export --user-id 12345
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
tg-msg-manager clean --dry-run
tg-msg-manager clean --apply --yes

# Run directly via python module:
python -m tg_msg_manager.cli clean --dry-run
```

### 📥 2. Export Mode (`export`)
Locates a target user's entire footprint and extracts their messages into elegantly formatted text files, complete with chronological order and embedded replies. Lookups are executed with a **concurrency pool of 10** for ultra-fast speeds, saving all data to an auto-created `PUBLIC_GROUPS` folder.

**Flags & Arguments:**
* `--user-id` *(Required)* — The numeric ID or username of the targeted entity.
* `--chat-id` *(Optional)* — Restrict scanning to a specific chat. If omitted, performs a global parallel scan.
* `--out` *(Optional)* — A custom filename for the output.
* `--json` — 📦 Export in **JSONL** format (one line per message object). Preferred for data analysis.
* `--deep` — 🧬 **Deep Search Mode.** Enables context retrieval. Finds target messages and stitches surrounding conversation fragments.

**Deep Mode Tuning:**
* `--context-window` — Context size (0 - target only, 1+ - find neighbors).
* `--time-threshold` — Connection threshold in seconds (default: 120).
* `--max-cluster` — Message limit per context fragment (default: 15).

**Examples:**
```bash
# Standard text export across all chats
tg-msg-manager export --user-id 1234567

# Deep JSONL export from a specific group
tg-msg-manager export --user-id "spammer" --chat-id -100123 --json --deep
```

### 🔄 3. Update Mode (`update`)
The smart updater. Scans your `PUBLIC_GROUPS` cache and performs high-concurrency fetching of new data. It automatically detects if a file was JSONL or TXT and if it was a Deep or Normal export.

**Flags:**
* `--json` — Update only `.jsonl` files.
* `--deep` — Update in deep context search mode.

**Examples:**
```bash
tg-msg-manager update
```

### 💬 4. Private Chat Archive (`export-pm`)
A complete backup of a private (direct message) conversation: text + **all media files** (photos, videos, video notes / circles, voice messages, GIFs, documents). Media is automatically sorted into dedicated subfolders inside `PRIVAT_DIALOGS/Name_@username_ID/media/`.

> ⚙️ **Built-in safeguards:** Incremental updates (only fetches new data), 50 MB per-file size limit, smart download throttler (emulates normal user behavior).

**Flags & Arguments:**
* `--user-id` *(Required)* — The numeric ID or username of the user whose DM thread to archive.

**Examples:**
```bash
tg-msg-manager export-pm --user-id 5378570247
tg-msg-manager export-pm --user-id "johndoe"
```

**Output structure:**
```
PRIVAT_DIALOGS/
└── John Doe_@johndoe_+79991234567_5378570247/
    ├── chat_log.txt
    └── media/
        ├── photos/
        ├── videos/
        ├── video_notes/
        ├── voices/
        ├── gifs/
        └── documents/
```

### ⏳ 5. Auto-Clean Daemon (`schedule`)
The state-of-the-art "self-destruct timer" setup. By asking a few simple questions in the console (time intervals, exclusion tracking), the utility instantly wraps itself around a native OS background daemon (`launchd` on macOS, `cron` on Linux, Task Scheduler on Windows). Your messages will be relentlessly and seamlessly scrubbed from the internet autonomously in the background!

**Examples:**
```bash
tg-msg-manager schedule
```

### 🌍 6. Global Flags
**`--config-dir`** — Instructs the tool to fetch its configuration from a specific directory path.
```bash
tg-msg-manager --config-dir /etc/tg_cleaner clean --apply --yes
```
