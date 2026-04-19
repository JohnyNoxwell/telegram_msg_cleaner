# 🧹 Telegram Message Cleaner & Exporter

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский

CLI-утилита на базе `telethon` для продвинутого управления сообщениями в Telegram. Забудьте о рутинной ручной чистке: скрипт позволяет массово и безопасно очищать историю своих сообщений или молниеносно выгружать чужую.

### 🌟 Главные функции

* 🧹 **Тотальная очистка (`clean`)**
  Удаляет **только ваши** сообщения изо всех групп и каналов, в которых вы состоите на данный момент. 
  > Поддерживает `dry-run` (безопасную репетицию), фильтрацию по датам, типу контента (медиа/текст) и настройку белых/черных списков чатов. Грамотно обходит ошибки `FloodWait`.
  
* 🗄️ **SQLite база данных (New!)**
  Все ваши сообщения теперь автоматически сохраняются в структурированную базу данных `messages.db` (или `<имя_аккаунта>_messages.db`). 
  > Это гарантирует молниеносный поиск, отсутствие дубликатов и надежное хранение всех метаданных (реакции, история правок, контекст).

* 📥 **Умный экспорт (`export`)** — *Теперь Deep-First по умолчанию!*
  Скрипт сразу ищет не только сообщения цели, но и восстанавливает **контекст беседы** (3 сообщения вокруг каждой реплики). Больше не нужно указывать флаг `--deep` вручную.
  > Данные сохраняются параллельно в локальный файл (Text/JSONL) и в базу данных SQLite.

* 🔄 **Автономное обновление (`update`)**
  Обновляет все ваши архивы в один клик. Скрипт использует базу данных как "источник истины", мгновенно определяя новые сообщения и **автоматически применяя настройки из базы**, которые были заданы при первом экспорте.

* 🧬 **Золотой стандарт (Gold Standard)**
  В систему вшиты оптимальные параметры: `context-window 3` и `max-cluster 10`. Это позволяет получить исчерпывающий профиль пользователя с минимальным объемом лишних данных.

* ⏳ **Таймер самоуничтожения (`schedule`)**
  Позволяет скрипту превратиться в системного демона. Укажите интервал, и он сам зарегистрируется в `launchd` / `cron` / `Windows Task Scheduler` для методичной очистки ваших сообщений в полном фоне!

* 💬 **Архив личной переписки (`export-pm`)**
  Полное резервное копирование приватного диалога с любым пользователем: текст и **все медиафайлы** (фото, видео, кружки, голосовые, GIF-анимации, документы). Медиа автоматически сортируются по папкам, лимит 50 МБ на файл, инкрементальное обновление.

* 🗑️ **Полная очистка данных пользователя (`delete`)**
  Позволяет мгновенно и безвозвратно стереть все сведения о конкретной цели: удаляет сообщения из базы данных и все скачанные файлы/папки из локального хранилища. Предварительно запрашивает подтверждение для безопасности.

---

### 💻 Установка (Windows / macOS / Linux)

Утилита написана на Python и является полностью кроссплатформенной (требуется версия **3.9 или выше**). 

**Шаг 1. Откройте терминал**
Перейдите в папку с проектом (туда, где лежит файл `pyproject.toml`).

**Шаг 2. Создание виртуального окружения (рекомендуется)**
* 🪟 **Windows (CMD/PowerShell):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```
* 🍎🐧 **macOS / Linux (Terminal):**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

**Шаг 3. Установка пакета**
```bash
pip install .
```
> 💡 **Примечание для Windows:** Если после установки команда `tg-msg-manager` не распознана, убедитесь, что путь к скриптам Python добавлен в переменную среды `PATH`, либо запускайте утилиту альтернативной командой `python -m tg_msg_manager.cli`

**Шаг 4. Установка быстрых алиасов (опционально)**
```bash
tg-msg-manager setup
```
Эта команда автоматически пропишет в ваш терминал (`~/.zshrc`, `~/.bashrc` или создаст `.bat`-файлы на Windows) набор коротких команд с уже вшитыми правильными путями к Python и к вашему проекту. После этого вместо длинных команд вы сможете писать:

| Алиас | Описание |
|--------|----------|
| `tg`   | 📖 Показать справку по всем алиасам |
| `tgr`  | 🛡️ Репетиция удаления (dry-run) |
| `tgd`  | 🧨 Боевое удаление сообщений |
| `tge`  | 📥 Экспорт сообщений из групп (напр.: `tge 12345`) |
| `tgu`  | 🔄 Обновить все экспорты |
| `tgpm` | 💬 Архив личной переписки с медиа (напр.: `tgpm 12345`) |
| `tgdel`| 🗑️ Полное удаление данных о пользователе (БД + файлы) |

---

### ⚙️ Конфигурация (`config.local.json`)

Скопируйте пример файла `config.example.json` и назовите его `config.local.json`. Положите его в ту же директорию, откуда планируете запускать скрипт.

**Ключевые параметры для удаления (`clean`):**
- `api_id` / `api_hash`: ваши ключи разработчика (можно получить на [my.telegram.org](https://my.telegram.org)).
- `account_name`: (опционально) имя вашего аккаунта. Если указано, файлы сессии и базы данных будут называться `<имя>_session` и `<имя>_messages.db`.
- `dry_run`: установите `true`, чтобы посмотреть статистику предстоящего удаления без риска. Установите `false` для реального удаления.
- `min_date_days_ago`: ограничить удаление временными рамками (например, `30` — удалить только то, что отправлено за последние 30 дней).
- `include_chats` / `exclude_chats` / `exclude_chat_titles`: настройка белых и черных списков.

---

### 🚀 Быстрый старт

Более подробное описание всех аргументов командной строки смотрите в отдельном справочнике: **[COMMANDS.md](COMMANDS.md)**.

**Примеры:**
```bash
# Репетиция удаления (посмотрит сколько удалит, но ничего не тронет)
tg-msg-manager clean --dry-run --yes

# Экспорт всей истории сообщений с контекстом (Золотой Стандарт)
tg-msg-manager export --user-id 1234567

# Инкрементальное обновление ВСЕХ целей из базы с учетом их индивидуальных настроек
tg-msg-manager update --json

# Принудительный сброс истории и перекачка с новой глубиной
tg-msg-manager update --force-resync --context-window 5
```

---
---

<a id="english"></a>
## 🇬🇧 English

A `telethon`-based CLI utility for advanced Telegram message management. Forget about manual cleaning: this script allows you to safely bulk-delete your messages or perform lightning-fast history exports of targeted users.

### 🌟 Key Features

* 🧹 **Message Deletion (`clean`)**
  Deletes **your** messages from any group chats and channels you are currently a member of.
  > Supports `dry-run` rehearsal mode, specific date filtering, message type filtering, and chat white/blacklists. Intelligently prevents and handles `FloodWait` errors.
  
* 📥 **Context-Aware Export (`export`)** — *Deep-First by default!*
  The script now retrieves not just the target's messages but also the **surrounding conversation** (3 messages around each reply by default). Manual `--deep` flag is no longer required.
  > Data is saved concurrently to a local file (Text/JSONL) and the SQLite database.

* 🔄 **Autonomous Mass Updater (`update`)**
  Sync all your archives with a single command. The tool uses the SQLite database as the "Source of Truth," instantly finding new messages and **automatically applying the configuration** (depth, window size) saved during the initial export.

* 🧬 **Gold Standard Analytics**
  Includes pre-configured "balanced" settings: `context-window 3` and `max-cluster 10`. Provides a complete behavior profile with full context while keeping the database lean and optimized.

* ⏳ **Self-Destruct Daemon (`schedule`)**
  Instantly metamorphosize the tool into a background orchestrator. It registers natively with `launchd` / `cron` / `Task Scheduler` to scrub your footprint automatically in complete stealth mode.

* 💬 **Private Chat Archive (`export-pm`)**
  Full backup of private conversations with any user: text and **all media files** (photos, videos, circles, voice messages, GIFs, documents). Media is auto-sorted into categorized folders, with a 50 MB per-file limit and incremental updates.

* 🗑️ **User Data Disposal (`delete`)**
  Instantly and permanently erases all records for a specific target: purges messages from the database and deletes all downloaded files/folders from local storage. Always asks for confirmation to prevent accidental loss.

---

### 💻 Installation (Windows / macOS / Linux)

The utility is thoroughly cross-platform but requires **Python 3.9+**.

**Step 1. Open your terminal**
Navigate to the root directory (where `pyproject.toml` is located).

**Step 2. Create a virtual environment (Recommended)**
* 🪟 **Windows (CMD/PowerShell):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```
* 🍎🐧 **macOS / Linux (Terminal):**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

**Step 3. Install the package**
```bash
pip install .
```
> 💡 **Note for Windows users:** If the `tg-msg-manager` command is not recognized post-installation, ensure your Python scripts folder is added to your environment `PATH` variable, or run the tool via `python -m tg_msg_manager.cli`.

**Step 4. Install quick aliases (Optional)**
```bash
tg-msg-manager setup
```
This command automatically configures short terminal aliases in your shell (`~/.zshrc`, `~/.bashrc`, or creates `.bat` files on Windows) with the correct paths to Python and your project directory already baked in. After this, instead of lengthy commands you can simply type:

| Alias  | Description |
|--------|-------------|
| `tg`   | 📖 Show the aliases cheatsheet |
| `tgr`  | 🛡️ Dry-run deletion rehearsal |
| `tgd`  | 🧨 Real message deletion |
| `tge`  | 📥 Export messages from groups (e.g. `tge 12345`) |
| `tgu`  | 🔄 Update all exports |
| `tgpm` | 💬 Archive a private chat with media (e.g. `tgpm 12345`) |
| `tgdel`| 🗑️ Full disposal of user data (DB + Files) |

---

### ⚙️ Configuration (`config.local.json`)

Copy `config.example.json` and optionally rename it to `config.local.json` in your execution directory.

**Crucial parameters for deleting (`clean`):**
- `api_id` / `api_hash`: get these from [my.telegram.org](https://my.telegram.org).
- `dry_run`: set `true` to test the script without actual deletion. Set `false` for real deletions.
- `min_date_days_ago`: limit to the past X days (e.g., `30`).
- `include_chats` / `exclude_chats`: tweak chat allowances.

---

### 🚀 Quick Start

For an exhaustive and comprehensive guide on commands and flags, please refer to **[COMMANDS.md](COMMANDS.md)**.

**Examples:**
```bash
# Репетиция удаления (посмотрит сколько удалит, но ничего не тронет)
tg-msg-manager clean --dry-run --yes

# Экспорт истории с полным контекстом (Золотой Стандарт теперь по умолчанию!)
tg-msg-manager export --user-id 1234567

# Инкрементальное обновление всех выгрузок с учетом их настроек из базы
tg-msg-manager update --json
```

---
---

<a id="english"></a>
## 🇬🇧 English

A `telethon`-based CLI utility for advanced Telegram message management. Forget about manual cleaning: this script allows you to safely bulk-delete your messages or perform context-aware history exports of targeted users.

### 🌟 Key Features

* 🧹 **Message Deletion (`clean`)**
  Deletes **your** messages from any group chats and channels you are currently a member of.
  > Supports `dry-run` rehearsal mode, specific date filtering, message type filtering, and chat white/blacklists. Intelligently prevents and handles `FloodWait` errors.
  
* 📥 **Context-Aware Export (`export`)** — *Deep-First by default!*
  The script now retrieves not just the target's messages but also the **surrounding conversation** (3 messages around each reply by default). Manual `--deep` flag is no longer required.
  > Data is saved concurrently to a local file (Text/JSONL) and the SQLite database.

* 🔄 **Autonomous Mass Updater (`update`)**
  Sync all your archives with a single command. The tool uses the SQLite database as the "Source of Truth," instantly finding new messages and **automatically applying the configuration** (depth, window size) saved during the initial export.

* 🧬 **Gold Standard Analytics**
  Includes pre-configured "balanced" settings: `context-window 3` and `max-cluster 10`. Provides a complete behavior profile with full context while keeping the database lean and optimized.

* ⏳ **Self-Destruct Daemon (`schedule`)**
  Instantly metamorphosize the tool into a background orchestrator. It registers natively with `launchd` / `cron` / `Task Scheduler` to scrub your footprint automatically in complete stealth mode.

* 💬 **Private Chat Archive (`export-pm`)**
  Full backup of private conversations with any user: text and **all media files** (photos, videos, circles, voice messages, GIFs, documents). Media is auto-sorted into categorized folders, with a 50 MB per-file limit and incremental updates.

---

### 💻 Installation (Windows / macOS / Linux)

The utility is thoroughly cross-platform but requires **Python 3.9+**.

**Step 1. Open your terminal**
Navigate to the root directory (where `pyproject.toml` is located).

**Step 2. Create a virtual environment (Recommended)**
* 🪟 **Windows (CMD/PowerShell):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```
* 🍎🐧 **macOS / Linux (Terminal):**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

**Step 3. Install the package**
```bash
pip install .
```
> 💡 **Note for Windows users:** If the `tg-msg-manager` command is not recognized post-installation, ensure your Python scripts folder is added to your environment `PATH` variable, or run the tool via `python -m tg_msg_manager.cli`.

**Step 4. Install quick aliases (Optional)**
```bash
tg-msg-manager setup
```
This command automatically configures short terminal aliases in your shell (`~/.zshrc`, `~/.bashrc`, or creates `.bat` files on Windows) with the correct paths to Python and your project directory already baked in. After this, instead of lengthy commands you can simply type:

| Alias  | Description |
|--------|-------------|
| `tg`   | 📖 Show the aliases cheatsheet |
| `tgr`  | 🛡️ Dry-run deletion rehearsal |
| `tgd`  | 🧨 Real message deletion |
| `tge`  | 📥 Export messages from groups (e.g. `tge 12345`) |
| `tgu`  | 🔄 Update all exports |
| `tgpm` | 💬 Archive a private chat with media (e.g. `tgpm 12345`) |

---

### ⚙️ Configuration (`config.local.json`)

Copy `config.example.json` and optionally rename it to `config.local.json` in your execution directory.

**Crucial parameters for deleting (`clean`):**
- `api_id` / `api_hash`: get these from [my.telegram.org](https://my.telegram.org).
- `dry_run`: set `true` to test the script without actual deletion. Set `false` for real deletions.
- `min_date_days_ago`: limit to the past X days (e.g., `30`).
- `include_chats` / `exclude_chats`: tweak chat allowances.

---

### 🚀 Quick Start

For an exhaustive and comprehensive guide on commands and flags, please refer to **[COMMANDS.md](COMMANDS.md)**.

**Examples:**
```bash
# Dry-run deletion
tg-msg-manager clean --dry-run --yes

# Export with full context (Gold Standard is now default!)
tg-msg-manager export --user-id 1234567

# Fast incremental update of all locally exported users using DB settings
tg-msg-manager update
```
