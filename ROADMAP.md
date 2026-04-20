# ROADMAP: TG_MSG_MNGR EVOLUTION

## 0. MISSION GOAL

Refactor the existing utility into a deterministic, layered, and high-performance system.
- **Strict Data Integrity**: Atomic operations, no duplicates.
- **Layered Architecture**: Decoupled Core, Infrastructure, and Services.
- **Idempotent Operations**: Reproducible results across runs.
- **Auditability**: Structured logs for every action.

---

# 1. DATA MODEL LAYER
- [x] **1.1** Implement `MessageData` Class.
- [x] **1.2** Unique Message Logic: `(chat_id, message_id)`.
- [x] **1.3** Schema Evolution Foundation.

# 2. STORAGE LAYER
- [x] **2.1** Storage Abstraction Interface.
- [x] **2.2** SQLite Backend with WAL mode.
- [x] **2.3** Legacy JSONL Import Logic.

# 3. DEDUPLICATION & INTEGRITY
- [x] **3.1** DB Pre-Check Mechanism.
- [x] **3.2** Payload Hashing.

# 4. TELEGRAM CORE (TELETHON)
- [x] **4.1** Client Wrapper & Abstraction.
- [x] **4.2** Throttling & RPS Limitation.
- [x] **4.3** Automatic FloodWait Interceptor.

# 5. EXPORT & DEEP MODE
- [x] **5.1** Core Sync Pipeline.
- [x] **5.2** Context Window Recursive Fetching.

# 6. UPDATE & SYNC SYSTEM
- [x] **6.1** Persistent Sync State.
- [x] **6.2** Smart Delta Updates.

# 7. CLEANER SYSTEM
- [x] **7.1** Whitelist Safety Engine.
- [x] **7.2** Atomic Self-Deletion.

# 8. SCHEDULING & CONCURRENCY
- [x] **8.1** File-based Locking.
- [x] **8.2** Signal Handling for Graceful Exit.

# 9. CONFIGURATION SYSTEM
- [x] **9.1** Pydantic Schema Validation.
- [x] **9.2** Environment Overrides.

# 10. OBSERVABILITY
- [x] **10.1** JSON & Human-readable Loggers.
- [x] **10.2** Detailed Telemetry.

# 11. TESTING FRAMEWORK
- [x] **11.1** SQLite Memory CRUD Tests.
- [x] **11.2** MOCKED Telegram Integration Tests.

# 12. COMPLETION CRITERIA (CHECKLIST)
- [x] 100% Deterministic Sync.
- [x] Zero Duplicate Records.
- [x] O(N) Efficiency.

---

# 13. PHASE: UX REVOLUTION (VERSION 4.0)
Transform the utility into a high-fidelity terminal application.
- [x] **13.1** Premium 24-bit ANSI Gradient aesthetics.
- [x] **13.2** Raw Terminal Input (non-canonical mode) and ESC-key navigation.
- [x] **13.3** Interactive "Page-based" sub-menus with technical descriptions.
- [x] **13.4** Silent Start: Default logs suppressed for cleaner App experience.
- [x] **13.5** Modular refactoring into `core/`, `services/`, `infrastructure/`.

---

# 🚀 NEXT GENERATIONS

## PHASE 14: SCALABILITY & INTEGRATION
- [ ] **14.1** Multi-Account rotation system.
- [ ] **14.2** Web-based Dashboard (Next.js) for message visualization.
- [ ] **14.3** Advanced Semantic Search across all downloaded history.
