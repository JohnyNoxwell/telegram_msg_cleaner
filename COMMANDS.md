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
Ищет все сообщения заданного пользователя и выкачивает их. По умолчанию включен **Deep Search Mode** (глубокий контекст). Сообщения сохраняются в `messages.db` и файл в папке `PUBLIC_GROUPS`.

**Флаги и Аргументы:**
* `--user-id` *(Обязательный)* — ID или username целевого пользователя.
* `--flat` — ⚡️ **Плоский экспорт.** Отключить контекст (только сообщения автора). Удобно для быстрой выгрузки без лишних данных.
* `--force-resync` — 🧨 **Сброс истории.** Игнорировать сохраненный прогресс и перекачать всю историю реплик заново (полезно при изменении глубины).
* `--context-window` — Размер окна контекста (Золотой Стандарт: **3**).
* `--max-cluster` — Макс. сообщений в одном кластере контекста (дефолт: **10**).
* `--json` — Экспорт в формате **JSONL**.

**Примеры использования:**
```bash
# Стандартный экспорт с контекстом (window 3)
tg-msg-manager export --user-id 1234567

# Глубокий аудит: перекачать историю заново с окном 5
tg-msg-manager export --user-id "spammer" --force-resync --context-window 5
```

### 🔄 3. Режим обновления (`update`) — *Smart Sync*
Теперь это полностью автономная команда. Она больше не сканирует файлы, а берет список целей и их настройки прямо из базы данных.

**Особенности:**
* **Persistent Config**: Если вы один раз выгрузили пользователя с окном 5, `update` всегда будет использовать 5 для него.
* **Force Update**: `update --force-resync` заставит скрипт перепроверить всю историю по всем отслеживаемым пользователям.
* **Overrides**: Любой флаг (например, `--context-window`) переопределит настройки в базе для этого и всех последующих запусков.

**Примеры использования:**
```bash
# Просто обновить всё по графику
tg-msg-manager update

# Массово перевести всех на плоский экспорт и обновить
tg-msg-manager update --flat
```

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

### 🗑️ 6. Режим удаления данных (`delete`)
Полностью стирает локальную историю и настройки для конкретного пользователя.
> ⚠️ **Внимание**: Это действие удалит все сообщения из `messages.db` и все файлы в `PUBLIC_GROUPS`/`PRIVAT_DIALOGS` по ID цели.

**Флаги и Аргументы:**
* `--user-id` *(Обязательный)* — ID пользователя для удаления.
* `--yes` — Пропуск подтверждения.

**Примеры использования:**
```bash
tg-msg-manager delete --user-id 1234567
tg-msg-manager delete --user-id 999 --yes
```

### 🌍 7. Глобальные Флаги
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
Locates target users and extracts their messages. **Deep Search Mode** (window 3) is enabled by default. All data is synchronized between `messages.db` and local files.

**Flags & Arguments:**
* `--user-id` *(Required)* — Numeric ID or username.
* `--flat` — ⚡️ **Flat Export.** Disable context (author messages only). Saves space and time.
* `--force-resync` — 🧨 **Re-scan History.** Ignores current progress and re-downloads the entire history (useful for updating depth).
* `--context-window` — Context size (Gold Standard: **3**).
* `--max-cluster` — Message limit per context fragment (default: **10**).
* `--json` — Export in **JSONL** format.

**Examples:**
```bash
# Standard export with context (window 3)
tg-msg-manager export --user-id 1234567

# Deep audit: re-fetch history with window 5
tg-msg-manager export --user-id "spammer" --force-resync --context-window 5
```

### 🔄 3. Update Mode (`update`) — *Smart Sync*
A fully autonomous command. It retrieves targets and their individual configurations directly from the SQLite database.

**Key Features:**
* **Persistent Config**: Once an export is performed with a specific depth, `update` will remember and reuse those settings forever.
* **Force Update**: `update --force-resync` triggers a full historical re-audit for all registered targets.
* **Overrides**: Passing any flag (e.g., `--context-window`) will override the stored database setting for this and future runs.

**Examples:**
```bash
# Standard scheduled sync
tg-msg-manager update

# Bulk switch to flat exports
tg-msg-manager update --flat
```

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

### 🗑️ 6. Data Disposal Mode (`delete`)
Purges all local history and settings for a specific target.
> ⚠️ **Warning**: This action erases all messages from `messages.db` and any files/folders in `PUBLIC_GROUPS`/`PRIVAT_DIALOGS` belonging to this ID.

**Flags & Arguments:**
* `--user-id` *(Required)* — Target ID to purge.
* `--yes` — Bypasses the confirmation prompt.

**Examples:**
```bash
tg-msg-manager delete --user-id 1234567
tg-msg-manager delete --user-id 999 --yes
```

### 🌍 7. Global Flags
**`--config-dir`** — Instructs the tool to fetch its configuration from a specific directory path.
```bash
tg-msg-manager --config-dir /etc/tg_cleaner clean --apply --yes
```
