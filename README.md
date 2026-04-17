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
  Параллельный поиск и загрузка истории сообщений заданного пользователя. Сохраняет хронологию, контекст бесед (реплаи) и историю изменения никнеймов. 
  > ⚠️ **Важно:** Поиск происходит исключительно в тех чатах и группах, к которым имеет доступ ваш аккаунт. Все выгрузки автоматически складываются в папку `EXPORTED_USRS`.
  
* 🔄 **Массовое обновление (`update`)**
  Инкрементальное обновление базы экспортированных пользователей в один клик. Скрипт сам считывает профили из `EXPORTED_USRS` и докачивает только свежие сообщения, ведя подробный `changelog.txt`. За счет многопоточности работает в 10 раз быстрее!

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
> 💡 **Примечание для Windows:** Если после установки команда `tg-message-cleaner` не распознана, убедитесь, что путь к скриптам Python добавлен в переменную среды `PATH`, либо запускайте утилиту альтернативной командой `python -m tg_message_cleaner.cli`

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
tg-message-cleaner clean --dry-run --yes

# Экспорт всей истории сообщений спамера во всех ваших общих чатах
tg-message-cleaner export --user-id 1234567

# Быстрое инкрементальное обновление всех собранных текстовых файлов
tg-message-cleaner update
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
  Fast and highly concurrent scanning to download a specific user's chat history. It preserves chronological order, nickname histories, and the context of replied messages.
  > ⚠️ **Note:** Exporting via user ID is strictly limited to the groups that your own account has joined. All generated text files are automatically saved into the `EXPORTED_USRS` directory.
  
* 🔄 **Mass Updater (`update`)**
  One-click incremental update. The script automatically reads previously exported profiles from the `EXPORTED_USRS` folder and fetches only their newly written messages, logging all changes accurately to `changelog.txt`.

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
> 💡 **Note for Windows users:** If the `tg-message-cleaner` command is not recognized post-installation, ensure your Python scripts folder is added to your environment `PATH` variable, or run the tool via `python -m tg_message_cleaner.cli`.

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
tg-message-cleaner clean --dry-run --yes

# Export all messages of a spammer from all your common chats
tg-message-cleaner export --user-id 1234567

# Blazing fast incremental update of all locally exported users
tg-message-cleaner update
```
