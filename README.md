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
  
* 📥 **Умный экспорт (`export`)**
  Параллельный поиск и выгрузка истории сообщений. Поддерживает обычный текстовый режим или структурированный **JSONL**.
  > ⚠️ **Deep Mode:** Уникальный режим "глубокого поиска", который находит не только сообщения цели, но и восстанавливает контекст беседы (реплики и соседние сообщения) вокруг каждого найденного фрагмента.

* 🔄 **Массовое обновление (`update`)**
  Докачивает новые сообщения для всех локальных архивов в один клик. Умный сканер сам определяет формат (Text/JSONL) и режим (Normal/Deep) каждого файла и обновляет их соответствующим образом.

* ⏳ **Таймер самоуничтожения (`schedule`)**
  Позволяет скрипту превратиться в системного демона. Укажите интервал, и он сам зарегистрируется в `launchd` / `cron` / `Windows Task Scheduler` для методичной очистки ваших сообщений в полном фоне!

* 💬 **Архив личной переписки (`export-pm`)**
  Полное резервное копирование приватного диалога с любым пользователем: текст и **все медиафайлы** (фото, видео, кружки, голосовые, GIF-анимации, документы). Медиа автоматически сортируются по папкам, лимит 50 МБ на файл, инкрементальное обновление.

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

---

### ⚙️ Конфигурация (`config.local.json`)

Скопируйте пример файла `config.example.json` и назовите его `config.local.json`. Положите его в ту же директорию, откуда планируете запускать скрипт.

**Ключевые параметры для удаления (`clean`):**
- `api_id` / `api_hash`: ваши ключи разработчика (можно получить на [my.telegram.org](https://my.telegram.org)).
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

# Экспорт всей истории сообщений спамера во всех ваших общих чатах
tg-msg-manager export --user-id 1234567

# Быстрое инкрементальное обновление всех собранных текстовых файлов
tg-msg-manager update
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
  
* 📥 **Message Exporting (`export`)**
  Fast concurrent scanning. Supports both human-readable text and structured **JSONL** formats for further analysis.
  > ⚠️ **Deep Mode:** A unique "context-aware" export that not only finds target messages but also retrieves surrounding conversations and replies to reconstruct the full context of every interaction.

* 🔄 **Mass Updater (`update`)**
  One-click incremental update. The smart scanner automatically detects the format (Text/JSONL) and mode (Normal/Deep) of every local file and synchronizes them with the latest Telegram data.

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

# Export all messages of a spammer from all your common chats
tg-msg-manager export --user-id 1234567

# Blazing fast incremental update of all locally exported users
tg-msg-manager update
```
