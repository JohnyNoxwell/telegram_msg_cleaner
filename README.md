# 🧹 TG_MSG_MNGR: Advanced Telegram Suite

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский

**TG_MSG_MNGR** — это мощная экосистема для управления вашим цифровым следом в Telegram. Переосмысленная в версии 4.0, утилита превратилась из простого скрипта в полноценное консольное Android-подобное приложение с фокусом на UX, скорость и надежность.

### 💎 Преимущества версии 4.0 (UX Revolution)

* 🎨 **Cyberpunk UI**: Полноцветная 24-битная ANSI градиентная шапка и премиальный дизайн интерфейса.
* ⚡ **Интерактивность**: Навигация в одно касание (нажатие цифры сразу выполняет действие) и поддержка клавиши **ESC** для мгновенной отмены или возврата назад.
* 🏗️ **Модульная архитектура**: Полностью переписанное ядро на базе сервисов (`ExportService`, `CleanerService`, `ArchiveService`), что гарантирует стабильность и легкость обновлений.
* 📖 **Контекстное обучение**: Каждое подменю снабжено краткой справкой о том, как работает конкретный алгоритм.

### 🌟 Главные функции

* 🧹 **Глобальная очистка (`clean`)**
  Удаляет **только ваши** сообщения изо всех чатов. Поддерживает белые списки и умный обход FloodWait.
  
* 📥 **Умный экспорт с контекстом (`export`)**
  Собирает сообщения цели вместе с «окном» беседы (реплики до и после), восстанавливая полную картину диалога.

* 🗄️ **SQLite Storage**
  Все данные превращаются в структурированную базу `messages.db`. Никакого дублирования, мгновенный доступ к миллионам записей.

* 💬 **Медиа-архив лички (`export-pm`)**
  Полный бэкап приватного чата: текст и все медиафайлы (фото, видео, документы), отсортированные по категориям.

* 📤 **Экспорт из БД (`db-export`)**
  Возможность выгрузить накопленные в SQLite данные в человекочитаемые форматы (JSON/Text).

---

### 💻 Установка и быстрый старт

1. **Клонируйте репозиторий** и установите зависимости через `pip install .`
2. **Алиасы**: Выполните `tg-msg-manager setup`, чтобы получить короткую команду `tg`.
3. **Запуск**: Просто введите `tg` в терминале для входа в интерактивное меню.

> 💡 **Навигация**: Используйте цифры **1-9** для выбора, **ESC** — назад/отмена, **0** — выход.

---
---

<a id="english"></a>
## 🇬🇧 English

**TG_MSG_MNGR** is a high-performance ecosystem for managing your digital footprint on Telegram. Reimagined in Version 4.0, the utility has evolved from a simple script into a robust, "app-like" terminal experience focusing on UX, speed, and deterministic data integrity.

### 💎 Version 4.0 Highlights (UX Revolution)

* 🎨 **Cyberpunk UI**: Vibrant 24-bit ANSI gradient banners and a premium, high-fidelity interface design.
* ⚡ **Ultra-Responsive**: Single-key navigation (press a number to act immediately) and full **ESC** key support for instant cancellation or "back" navigation.
* 🏗️ **Service-Oriented Core**: Completely refactored modular architecture (`ExportService`, `CleanerService`, `ArchiveService`) ensuring long-term stability and easier auditing.
* 📖 **In-App Guidance**: Every sub-menu features technical descriptions of how the specific engine works.

### 🌟 Core Features

* 🧹 **Global Cleanup (`clean`)**
  Removes **your own** messages from all currently joined group chats. Respects whitelists and handles FloorWait errors gracefully.
  
* 📥 **Deep Context Export (`export`)**
  Automatically retrieves target messages along with the "surrounding" conversation window, providing a complete picture of the dialogue.

* 🗄️ **SQLite Source of Truth**
  All messages are stored in a structured `messages.db`. Ensures zero duplicates and instant querying across millions of records.

* 💬 **Media Archive (`export-pm`)**
  Total backup for private conversations: text and **all media types** (photos, videos, voice notes), auto-sorted into categorized folders.

* 📤 **Database Export (`db-export`)**
  Native service to export collected SQLite records into human-readable formats (JSON/TXT).

---

### 💻 Installation & Quick Start

1. **Clone & Install**: Run `pip install .` in the root directory.
2. **Aliases**: Execute `tg-msg-manager setup` to register the `tg` shortcut.
3. **Launch**: Simply type `tg` in your terminal to enter the premium interactive menu.

> 💡 **Navigation Tip**: Use numbers **1-9** to select, **ESC** to go back/cancel, and **0** to exit.
