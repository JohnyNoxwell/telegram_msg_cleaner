# VPS Docker Compose deployment

Эта инструкция описывает ручной запуск `tg-msg-manager` на Ubuntu 24.04 VPS через Docker Compose. Контейнер запускает существующий CLI из текущего checkout и не должен содержать пользовательские секреты, Telegram sessions, SQLite базы, exports или logs.

## Требования

- Ubuntu 24.04 VPS.
- Установленные Docker Engine и Docker Compose plugin.
- Репозиторий клонирован в `/opt/tg-msg-manager`.
- Постоянное состояние хранится на хосте в `/opt/tg-msg-manager/state`.

## Подготовка VPS

```bash
sudo mkdir -p /opt/tg-msg-manager
sudo chown "$USER:$USER" /opt/tg-msg-manager
git clone https://github.com/JohnyNoxwell/tg-msg-manager.git /opt/tg-msg-manager
cd /opt/tg-msg-manager
mkdir -p state
docker compose build
```

Скопируйте или создайте `config.json` и Telegram session только внутри `/opt/tg-msg-manager/state`. Не добавляйте эти файлы в image, commits, issues или PR.

## Запуск

```bash
cd /opt/tg-msg-manager
docker compose run --rm tg-msg-manager --help
docker compose run --rm tg-msg-manager update
docker compose run --rm tg-msg-manager export --user-id 123456789 --chat-id 987654321 --json
```

Запуск без аргументов сохраняет интерактивный режим:

```bash
docker compose run --rm tg-msg-manager
```

## Shell helpers

```bash
cd /opt/tg-msg-manager
./deploy/vps/install-shell.sh
source /opt/tg-msg-manager/deploy/vps/tg-shell.sh
```

Доступные функции:

```bash
tg --help
tgu
tge 123456789
tgpm 123456789
tgh 123456789
tgr
tgd
```

Внимание: `tgd` запускает `clean --apply --yes`. Перед ним используйте `tgr`, чтобы проверить dry-run.

## Systemd schedule

Планировщик на VPS не использует cron и не зависит от shell aliases или `~/.bashrc`. Все scheduled-запуски проходят через:

```bash
/opt/tg-msg-manager/deploy/vps/run-scheduled.sh
```

Launcher вызывает `/opt/tg-msg-manager/deploy/vps/tgm` с переданными аргументами и использует общий non-blocking lock:

```text
/run/lock/tg-msg-manager-scheduler.lock
```

Если lock занят, запуск пропускается с exit code `75`; для systemd это настроено как successful skip. Общий lock не допускает одновременную работу scheduled `tgu` (`update`) и scheduled `tgd` (`clean --apply --yes`). Логи остаются только в `journalctl`.

Расписание указано прямо в `OnCalendar` с timezone `Europe/Kyiv`; timezone всей VPS не меняется. `Persistent=true` не используется, поэтому пропущенные во время выключенного сервера запуски не выполняются при следующей загрузке.

- `tg-msg-manager-update.timer`: каждые 10 минут по `Europe/Kyiv`.
- `tg-msg-manager-clean.timer`: каждый день ровно в `04:35` по `Europe/Kyiv`.

`tgd` является destructive-командой `clean --apply --yes`: она удаляет
сообщения текущего аккаунта из Telegram, но сохраняет уже записанные сообщения
и связи контекста в локальной SQLite. Не запускайте clean service вручную для
проверки.

Установка timers:

```bash
cd /opt/tg-msg-manager
sudo ./deploy/vps/install-systemd-schedules.sh
```

Проверка:

```bash
systemctl list-timers 'tg-msg-manager-*'
systemctl status tg-msg-manager-update.timer
systemctl status tg-msg-manager-clean.timer
journalctl -u tg-msg-manager-update.service
journalctl -u tg-msg-manager-clean.service
```

Откат:

```bash
sudo systemctl disable --now tg-msg-manager-update.timer tg-msg-manager-clean.timer
sudo rm -f /etc/systemd/system/tg-msg-manager-update.service
sudo rm -f /etc/systemd/system/tg-msg-manager-update.timer
sudo rm -f /etc/systemd/system/tg-msg-manager-clean.service
sudo rm -f /etc/systemd/system/tg-msg-manager-clean.timer
sudo systemctl daemon-reload
```

## Перенос состояния с Mac

На локальной машине остановите локальный запуск приложения перед push, чтобы не копировать состояние во время записи.

По умолчанию local source — корень текущего checkout, из которого запускается helper, например `/Users/maczone/dev/tg-msg-manager`. Это удобно, если runtime-файлы лежат рядом с исходным кодом, но helper синхронизирует только allowlist runtime state, а не исходный код, `.git`, `docs`, `tests`, `deploy`, virtualenv или build artifacts.

```bash
cd /Users/maczone/dev/tg-msg-manager
export TGMM_SSH_HOST=vps
export TGMM_REMOTE_STATE_DIR=/opt/tg-msg-manager/state

./deploy/local/tg-state-sync.sh push --dry-run
./deploy/local/tg-state-sync.sh push --apply
./deploy/local/tg-state-sync.sh pull exports
./deploy/local/tg-state-sync.sh pull logs
./deploy/local/tg-state-sync.sh pull all
```

Если state находится не в checkout root, задайте `TGMM_LOCAL_STATE_DIR` вручную перед запуском.

`push` передаёт только:

- `config.json`, `config.local.json`, `DB_TARGETS.txt`, `delete_log.txt`;
- root-level `*.log`;
- root-level Telegram `*.session` вместе с `*.session-shm`, `*.session-wal`, `*.session-journal`;
- root-level SQLite `*.db`, `*.sqlite`, `*.sqlite3` вместе с WAL/SHM/journal sidecars;
- `*_state.json` из поддерживаемых runtime state-файлов;
- директории `DB_EXPORTS/`, `PUBLIC_GROUPS/`, `PRIVAT_DIALOGS/`, `exports/`, `LOGS/`.

`.tg_msg_manager.lock` не синхронизируется. Если lock существует, helper выводит предупреждение; остановите локальное приложение и повторите push.

`pull exports` забирает только export directories: `exports/`, `DB_EXPORTS/`, `PUBLIC_GROUPS/`, `PRIVAT_DIALOGS/`. `pull logs` забирает `LOGS/`, `delete_log.txt` и root-level `*.log`. Pull не загружает обратно `config.json`, `config.local.json`, Telegram sessions или SQLite databases.

Sync helper использует `rsync` over SSH, archive mode, compression, `--partial` и `--info=progress2`. Он не использует `--delete`.

Не коммитьте `config.json`, `config.local.json`, Telegram sessions, SQLite databases, exports или logs; не прикладывайте их к PR/issues и не включайте в Docker image.
