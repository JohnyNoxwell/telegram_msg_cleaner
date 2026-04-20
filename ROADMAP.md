# ROADMAP: TG.MSG.CLEANER SYSTEM EVOLUTION

## 0. MISSION GOAL

Refactor the existing utility into a deterministic, layered, and high-performance system.
- **Strict Data Integrity**: Atomic operations, no duplicates.
- **Layered Architecture**: Decoupled Core, Infrastructure, and Services.
- **Idempotent Operations**: Reproducible results across runs.
- **Auditability**: Structured logs for every action.

---

# 1. DATA MODEL LAYER

## 1.1 MESSAGE SCHEMA SPECIFICATION
- [x] **1.1.1** Initialize Model Directory: Create `tg_msg_manager/core/models/` and `__init__.py`.
- [x] **1.1.2** Create `message.py`: Define the core data structure.
- [x] **1.1.3** Implement `MessageData` Class:
    - Use `dataclasses.dataclass` with `@dataclass(frozen=True)`.
    - Fields: `message_id`, `chat_id`, `user_id`, `timestamp` (UTC), `text`, `media_type`, `reply_to_id`, `fwd_from_id`, `context_group_id`, `raw_payload`.
- [x] **1.1.4** Type Validation: Add `__post_init__` to ensure `timestamp` is a `datetime` object and IDs are integers.
- [x] **1.1.5** Serialization:
    - Implement `to_dict()` for storage.
    - Implement `from_dict()` factory method.

## 1.2 UNIQUENESS & CONSTRAINTS
- [x] **1.2.1** Logic Definition: Unique Message = `(chat_id, message_id)`.
- [x] **1.2.2** Key Generator: Implement `get_message_key(msg: MessageData) -> str` returning `chat:msg` format.

## 1.3 SCHEMA EVOLUTION
- [x] **1.3.1** Version Tracking: Define `SCHEMA_VERSION = 1` in `message.py`.
- [ ] **1.3.2** Migration Model: Define an abstract `Migration` class for future data transforms.

---

# 2. STORAGE LAYER

## 2.1 ABSTRACTION INTERFACE
- [x] **2.1.1** Initialize Infrastructure: Create `tg_msg_manager/infrastructure/storage/` and `__init__.py`.
- [x] **2.1.2** Create `interface.py`: Define `BaseStorage(ABC)`.
- [x] **2.1.3** Define Contract:
    - `save_message(msg: MessageData) -> bool`
    - `save_messages(msgs: List[MessageData]) -> int`
    - `get_message(chat_id, msg_id) -> Optional[MessageData]`
    - `message_exists(chat_id, msg_id) -> bool`
    - `get_last_msg_id(chat_id) -> int`

## 2.2 SQLITE BACKEND IMPLEMENTATION
- [x] **2.2.1** Create `sqlite.py`: Implement `SQLiteStorage(BaseStorage)`.
- [x] **2.2.2** Connection Handling: Implement context manager for SQLite connections with `WAL` mode enabled.
- [x] **2.2.3** Schema Deployment: Implement `_init_db()` to create `messages` and `sync_state` tables.
- [x] **2.2.4** Atomic Operations: Use `INSERT OR REPLACE` for idempotent saving.

## 2.3 LEGACY COMPATIBILITY (JSONL/TXT)
- [x] **2.3.1** JSONL Scanner: Implement a tool to read old exported `.jsonl` files.
- [x] **2.3.2** Normalizer: Convert old JSON objects into new `MessageData` objects.
- [x] **2.3.3** Import Service: Implement `ImportLegacyService` to populate the new DB from old file backups.

---

# 3. DEDUPLICATION & INTEGRITY

## 3.1 DEDUPLICATION LOGIC
- [x] **3.1.1** Pre-Check Mechanism: Logic to check existence in DB before fetching media.
- [x] **3.1.2** Conflict Resolution: If `message_id` exists but `text` or `media` changed (edit), update the record.

## 3.2 HASHING
- [x] **3.2.1** Payload Integrity: Calculate SHA256 of core fields + `raw_payload` to verify data consistency during sync.

---

# 4. TELEGRAM CORE LAYER (TELETHON WRAPPER)

## 4.1 CLIENT ABSTRACTION
- [x] **4.1.1** Setup Core: Create `tg_msg_manager/core/telegram/`.
- [x] **4.1.2** Client Interface: Create `interface.py` and `TelegramClientInterface`.
- [x] **4.1.3** Implementation: Create `TelethonClientWrapper` implementing the interface.
- [x] **4.1.4** Method Hardening: Implement `iter_messages` with automatic error retries.

## 4.2 RATE LIMITING (THROTTLING)
- [x] **4.2.1** Throttler logic: Create `throttler.py`.
- [x] **4.2.2** Async Lock: Implement `RateThrottler(max_rps=3)`.
- [x] **4.2.3** Global Hook: Ensure every API call passes through the throttler decorator.

## 4.3 FLOODWAIT AUTOMATION
- [x] **4.3.1** Interceptor: Catch `FloodWaitError` globally in the wrapper.
- [x] **4.3.2** Smart Pause: Implement exponential backoff or strict `sleep(e.seconds)`.

---

# 5. EXPORT & DEEP MODE SERVICES

## 5.1 CORE EXPORTER
- [x] **5.1.1** Service Setup: Create `tg_msg_manager/services/exporter.py`.
- [x] **5.1.2** Export Pipeline: Fetch -> Model -> Dedup -> Storage.

## 5.2 DEEP CONTEXT EXTRACTION
- [x] **5.2.1** Rules Engine:
    - Define `WINDOW_BEFORE = 5`, `WINDOW_AFTER = 5`.
- [x] **5.2.2** Context Recursive Fetching:
    - Fetch N messages around target.
    - Fetch all replies to target.
    - Fetch original message if target is a reply.
- [x] **5.2.3** Clustering: Assign unique `context_group_id` (UUID) to all messages in the cluster.

---

# 6. UPDATE & SYNC SYSTEM

## 6.1 STATE MANAGEMENT
- [x] **6.1.1** Persist State: Create `sync_state` table in DB storing `{chat_id: last_processed_id}`.
- [x] **6.1.2** Smart Filter: Query DB to find targets that haven't been updated for > 24 hours.

## 6.2 INCREMENTAL SYNC
- [x] **6.2.1** Delta Fetch: Only request messages with `id > last_processed_id`.
- [x] **6.2.2** Consistency Check: Verify count of messages in DB matches metadata from Telegram.

---

# 7. CLEANER SYSTEM (DELETION)

## 7.1 VALIDATION & SAFETY
- [x] **7.1.1** Config Check: Ensure target chat is not in the whitelist before deletion.
- [x] **7.1.2** Dry Run Logic: Implement `DryRunExecutor` that only logs intended deletions.

## 7.2 EXECUTION
- [x] **7.2.1** Atomic Deletion: Delete from Telegram, then mark as deleted in DB (soft-delete or purge).
- [x] **7.2.2** Confirmation: Force a `--yes` flag for any non-dry-run operation.

---

# 8. SCHEDULING & CONCURRENCY

## 8.1 LOCKING MECHANISM
- [x] **8.1.1** File Lock: Implement `.lock` file check to prevent multiple instances of `update`.
- [x] **8.1.2** Signal Handling: Graceful shutdown on `SIGINT` (Ctrl+C), saving state before exit.

## 8.2 RETRY LOGIC
- [x] **8.2.1** Task Queue: Implement simple retry queue for failed message exports.

---

# 9. CONFIGURATION SYSTEM

## 9.1 SCHEMA VALIDATION
- [x] **9.1.1** Pydantic Config: Define `ConfigSchema` for `config.json`.
- [x] **9.1.2** Error Reporting: "Fail-fast" if API IDs or paths are missing/invalid.

## 9.2 ENVIRONMENT OVERRIDES
- [x] **9.2.1** Env Support: Allow `TG_API_ID` etc. to override JSON settings.

---

# 10. OBSERVABILITY

## 10.1 STRUCTURED LOGGING
- [x] **10.1.1** JSON Logger: Implement `JSONFormatter` for Python logging.
- [x] **10.1.2** Context Fields: Include `trace_id` and `chat_id` in every log line.

## 10.2 PERFORMANCE METRICS
- [x] **10.2.1** Telemetry: Track `api_requests`, `messages_saved_per_sec`, `flood_wait_total`.

---

# 11. TESTING FRAMEWORK

## 11.1 UNIT & COMPONENT TESTS
- [x] **11.1.1** Storage Tests: Test CRUD operations on a memory SQLite DB.
- [x] **11.1.2** Model Tests: Validate factory methods and serialization.

## 11.2 INTEGRATION & MOCKS
- [x] **11.2.1** Mock Telegram: Use `pytest-mock` to simulate Telethon responses.

---

# 12. COMPLETION CRITERIA (CHECKLIST)

- [x] All code passes `flake8` and `mypy` (strict types).
- [x] Zero duplicate messages in the final SQLite DB.
- [x] `update` command completes in O(N) relative to *new* messages only.
- [x] Deep Mode output is reproducible.
- [x] Structured logs show clear trace of actions.
