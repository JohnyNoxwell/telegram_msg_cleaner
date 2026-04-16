## tg-message-cleaner

CLI-утилита на базе Telethon для удаления **своих** сообщений из чатов Telegram.

- **Удаляет только ваши сообщения**
- Поддерживает **dry-run** (репетиция без реального удаления)
- Фильтры:
  - по дате (например, только за последние 30 дней);
  - по списку чатов (включить/исключить по ID и по названию);
  - по типу сообщений (текст, медиа, пересланные).
- Пакетное удаление и аккуратная работа с **FloodWait**.
- Логирование в файл.

---

### Установка

Находясь в папке `TG_CLEANER` (там, где лежит `pyproject.toml`):

```bash
pip install .
```

Требуется Python **3.9+**.

---

### Конфигурация (`config.local.json`)

Скрипт ищет конфиг в директории запуска по приоритету:
`config.local.json` (предпочтительный) или `config.json`.

В репозитории хранится только `TG_CLEANER/config.example.json` — скопируйте/создайте локальный `TG_CLEANER/config.local.json`.

Пример (`TG_CLEANER/config.example.json`):

```json
{
  "api_id": 123456,
  "api_hash": "YOUR_API_HASH",
  "session_name": "tg_delete_my_msgs",

  "dry_run": true,
  "min_date_days_ago": null,

  "include_chats": [],
  "exclude_chats": [],
  "exclude_chat_titles": [],

  "delete_media": true,
  "delete_text": true,
  "delete_forwards": true,

  "base_delay_sec": 0.15,
  "max_delay_sec": 5.0,
  "batch_size": 50
}
```

- **`api_id` / `api_hash`**: взять с `https://my.telegram.org`.
- **`dry_run`**:
  - `true` – только показывает, какие сообщения были бы удалены (без удаления);
  - `false` – реально удаляет сообщения.
- **`min_date_days_ago`**:
  - `null` – без ограничения по дате;
  - число (например, `30`) – удалять только сообщения за последние 30 дней.
- **`include_chats`**:
  - пусто или `null` – обрабатывать все чаты;
  - список ID чатов – обрабатывать только указанные.
- **`exclude_chats`**:
  - список ID чатов, которые нужно пропустить.
- **`exclude_chat_titles`**:
  - список названий чатов, которые нужно пропустить (сравнение case-insensitive по `dialog.name`/`dialog.title`).
- **`delete_media` / `delete_text` / `delete_forwards`**:
  - включить/отключить удаление медиа, текстов и пересланных сообщений.
- **`base_delay_sec` / `max_delay_sec` / `batch_size`**:
  - управляют скоростью и размером батча удаления, чтобы не ловить жёсткий FloodWait.

---

### Запуск

Доступные команды (после `pip install .` или через `python -m`):

#### 1. Удаление сообщений (clean)
Репетиция (без реального удаления):
```bash
tg-message-cleaner clean --dry-run --yes
# или по-старому:
tg-message-cleaner --dry-run --yes
```

Реальное удаление:
```bash
tg-message-cleaner clean --apply --yes
```

#### 2. Экспорт сообщений (export)
Инкрементально экспортирует историю сообщений пользователя в текстовый файл с сохранением хронологии и исходных (цитируемых) сообщений. По умолчанию все результаты сохраняются в папку `EXPORTED_USRS` и автоматически формируют имя файла.
```bash
# Глобальный поиск: найдет все сообщения юзера и сохранит их в EXPORTED_USRS/Экспорт_Ник_12345678.txt
tg-message-cleaner export --user-id 12345678

# Экспорт сообщений из конкретной группы (по ID или username)
tg-message-cleaner export --user-id "spammer_username" --chat-id -1001234567

# Указать кастомное имя файла в той же папке
tg-message-cleaner export --user-id 12345678 --out "my_export.txt"
```

Если команда `tg-message-cleaner` недоступна в `PATH`, можно запускать напрямую через Python:
```bash
python -m tg_message_cleaner.cli clean --dry-run --yes
python -m tg_message_cleaner.cli export --user-id 12345678
```

### Возможности и улучшения
- **Асинхронность:** корректная работа с `FloodWait` без блокировки цикла.
- **Умное логирование:** запись в файл `delete_log.txt` и вывод в консоль.
- **Полный проход:** каждый запуск повторно обрабатывает все найденные группы/каналы (progress state не используется).
- **Безопасность:** добавлена проверка наличия обязательных полей в конфиге.

По умолчанию:
- ищет `config.local.json` или `config.json` в текущей директории.
- спрашивает подтверждение перед запуском.
- в режиме `dry_run: true` только показывает количество сообщений.

Примечание про прогресс/переходы:
- сейчас каждый запуск делает полный проход по всем группам/каналам и `state` не используется.
- опции `--no-resume` и `--reset-state` оставлены для совместимости.

---

### Где смотреть лог

По умолчанию лог пишется в файл `delete_log.txt` в той же директории, что и локальный конфиг (`config.local.json`/`config.json`).

В логе фиксируется:

- какие чаты обрабатывались;
- сколько сообщений найдено/удалено;
- ошибки и события FloodWait.

---

## English

`tg-message-cleaner` is a CLI utility (based on Telethon) that deletes **your own** messages from Telegram group chats and channels.

### Install

```bash
cd TG_CLEANER
pip install .
```

### Configuration

Create `TG_CLEANER/config.local.json` (recommended) from `TG_CLEANER/config.example.json`.

The tool looks for `config.local.json` first, and then falls back to `config.json` in the **current working directory** (unless you set `TGMC_CONFIG_DIR`).

Extra filtering:
- `exclude_chats`: skip chats by ID
- `exclude_chat_titles`: skip chats by name/title (case-insensitive; matches `dialog.name` / `dialog.title`)

### Run

Dry-run (no deletion):

```bash
tg-message-cleaner --dry-run --yes
```

Real deletion:

```bash
tg-message-cleaner --apply --yes
```

If `tg-message-cleaner` is not in `PATH`, run without installation:

```bash
python -m tg_message_cleaner.cli --dry-run --yes
python -m tg_message_cleaner.cli --apply --yes
```

Progress/resume note:
- each run does a full sweep; `state` is not used
- `--no-resume` / `--reset-state` are kept only for backward compatibility

### Key Improvements
- **Async Fix:** Proper `FloodWait` handling without blocking the event loop.
- **Improved Logging:** File logging (`delete_log.txt`) plus console output.
- **Full Sweep Each Run:** Each run re-processes all groups/channels (progress state is not used).
- **Config Validation:** Validates required fields (`api_id`, `api_hash`) on startup.

