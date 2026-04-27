# TG_CLEANER TODO

## Operating Notes

- Live Telegram session from the project root may be used for validation.
- Live API requests are allowed for read/export and non-destructive chat inspection.
- Avoid ban-risk behavior: respect FloodWait, keep throttling conservative, do not brute-force retries.
- Store all live-test outputs in a separate temporary folder so they do not mix with working exports.
- Current live-test target:
  - `user_id`: `8603071440`
  - `chat_id`: `1274306614`

## Phase 0: Baseline

- [x] Reproduce current test failures and classify them by root cause.
- [x] Map all storage write call sites and all `sync_targets` schema usages.
- [x] Define the target storage contract after refactor.
- [x] Prepare an isolated live-test output directory convention.

## Phase 1: Storage Contract

- [x] Convert `BaseStorage` write methods to the actual async contract.
- [x] Update all write call sites to use `await`.
- [x] Verify no un-awaited storage writes remain.
- [x] Add storage contract tests for async single and batch writes.
- [x] Validate queue drain and shutdown behavior.

## Phase 2: SQLite Schema And Migrations

- [x] Add missing `last_sync_at` support to `sync_targets`.
- [x] Audit all `sync_targets` queries against the real schema.
- [x] Simplify migration flow for fresh and legacy databases.
- [x] Add migration tests for clean and legacy DB states.
- [x] Verify `get_outdated_chats` works on migrated databases.

## Phase 3: SQLite Storage Refactor

- [x] Split schema, write-path, read-path, and sync-state responsibilities.
- [x] Reduce `sqlite.py` complexity without changing external behavior.
- [x] Re-check lock discipline and connection usage.

## Phase 4: Test Suite Repair

- [x] Rewrite outdated config tests.
- [x] Rewrite storage tests for async writes.
- [x] Rewrite exporter/context tests for the current service API.
- [x] Rewrite sync-system tests for the current method signatures.
- [x] Replace process-signal tests with isolated handler tests.
- [x] Establish a stable smoke suite.

## Phase 5: Config Semantics

- [x] Define explicit precedence for init args, env, dotenv, and JSON config.
- [x] Make env override behavior deterministic.
- [x] Align legacy aliases with documented fields.
- [x] Improve startup error clarity.

## Phase 6: Export-PM Gap

- [x] Decide whether `export-pm` will really download media in this iteration.
- [x] If yes: extend Telegram client interface with media download support.
- [x] If yes: implement media download, routing, limits, and error handling.
- [x] If no: correct CLI/docs/i18n claims immediately.

## Phase 7: Docs And UX Alignment

- [x] Align README with actual behavior.
- [x] Align CLI help and aliases with actual behavior.
- [x] Align i18n strings with actual behavior.
- [x] Add known limitations section.

## Phase 8: CI And Quality Gates

- [ ] Add lint/format/test validation commands.
- [x] Add a minimal CI workflow.
- [x] Exclude cache and transient artifacts from source control hygiene.
- [x] Add a repeatable local verification checklist.

## Near-Term Execution Order

1. Add lint/format/test validation commands.
2. Keep `CHANGELOG.md` in sync with every shipped batch.

## Remediation Backlog

### Priority 1: Sync Correctness

- [x] Fix `get_outdated_chats` so old targets are not re-scanned forever after successful sync.
- [x] Fix target-specific `last_msg_id` updates so context messages do not advance another user's checkpoint.
- [x] Scope deep-mode processed IDs to a chat/sync-safe key to avoid cross-chat context loss.
- [x] Preserve `limit` when retrying `get_messages` after `FloodWait`.
- [x] Ensure PM archive writes target attribution links and refreshes target sync timestamps.

### Priority 2: Reliability And Cleanup

- [x] Fix CLI `delete` command initialization path.
- [x] Remove orphan `message_target_links` during message deletion and keep counts accurate.
- [x] Fix `_fetch_parent_replies` retry argument ordering.
- [x] Replace process-signal tests with isolated handler tests that do not interrupt the whole suite.

### Priority 3: Throughput And UX

- [x] Rework forced `flush()` behavior so the background writer can actually batch writes.
- [x] Make `--limit` semantics explicit and enforce them consistently across parallel workers.
- [x] Restore TXT export rotation resume behavior.
- [x] Document known limitations and add a repeatable verification checklist.

## Refactoring Program

### Baseline Metrics

- [x] Capture a static maintainability baseline for the current codebase.
  Current snapshot: `33` Python files, `300` functions, `28` classes, `924` branch nodes.
  Current hotspots by file complexity: `services/exporter.py` (`706` code LOC, `217` branches), `services/context_engine.py` (`821` code LOC, `160` branches), `cli.py` (`411` code LOC, `116` branches), `services/db_exporter.py` (`426` code LOC, `93` branches).
  Current hotspots by function complexity: `ExportService.sync_chat()` (`438` lines / `111` branches), `DBExportService.export_user_messages()` (`216` lines / `39` branches), `ExportService.scan_worker()` (`169` lines / `46` branches), `main_menu()` (`156` lines / `53` branches), `ExportService._sync_target_items()` (`148` lines / `56` branches).

### Planned Steps

- [x] Step 1: Decompose `ExportService.sync_chat()` preflight setup and scan-result finalization into focused helpers without changing behavior.
- [x] Step 2: Extract the nested scan worker / scan-buffer pipeline from `ExportService.sync_chat()` into smaller composable units.
  Current delta: `sync_chat()` is down to `185` lines / `19` branches, with the extracted scan pipeline now split across `_scan_range()` (`142` / `22`) and `_process_scan_buffer()` (`85` / `12`).
- [x] Step 3: Split shared head prefetch and target scheduling concerns out of `ExportService._sync_target_items()`.
  Current delta: `_sync_target_items()` is down to `78` lines / `8` branches, with shared prefetch planning moved to `_prime_shared_head_prefetch_cache()` (`47` / `8`) and per-target scheduling moved to `_plan_tracked_sync_target()` (`49` / `5`).
- [x] Step 4: Break `DBExportService.export_user_messages()` into source-selection, manifest, and writer-pipeline helpers.
  Current delta: `export_user_messages()` is down to `86` lines / `3` branches, with source selection in `_load_export_source()` (`23` / `6`), export planning in `_prepare_export_plan()` (`47` / `4`), and file emission in `_write_export_payloads()` (`62` / `13`).
- [x] Step 5: Break `cli.py` menu / command handlers into smaller command-specific entrypoints.
  Current delta: `run_cli()` is down to `29` lines / `3` branches and `main_menu()` to `21` / `5`, with CLI dispatch moved into command-specific handlers such as `_handle_export_command()` (`29` / `2`) and interactive routing centralized in `_dispatch_main_menu_choice()` (`22` / `4`).
- [x] Step 6: Decompose `DeepModeEngine` candidate-fetch and round-expansion logic into smaller focused helpers.
  Current delta: `_expand_structural_round()` is down to `40` lines / `1` branch, `_fetch_parent_messages()` to `25` / `2`, and `_fetch_candidate_pool()` to `39` / `3`, with the split candidate pipeline now isolated in `_collect_range_candidates()` (`35` / `2`) and `_fetch_live_range_fill()` (`38` / `4`).
- [x] Step 7: Re-run static metrics and compare hotspot deltas against the baseline.
  Current snapshot: `33` Python files, `358` functions, `32` classes, `881` branch nodes (`-43` vs baseline `924`).
  Hotspot delta by branch count: `services/exporter.py` `217 -> 191`, `cli.py` `116 -> 97`, `services/context_engine.py` `160 -> 158`; the main function hotspot moved from `ExportService.sync_chat()` (`111` branches at baseline) to `CleanerService.global_self_cleanup()` (`24` branches), with `sync_chat()` now at `19`.

## Follow-up Hotspots

- [x] Refactor `CleanerService.global_self_cleanup()` into dialog-filtering, self-message collection, and per-dialog execution helpers.
  Current delta: `global_self_cleanup()` is down to `31` lines / `3` branches, with eligibility routing moved to `_dialog_is_cleanup_eligible()` (`9` / `5`), dialog prefiltering to `_eligible_cleanup_dialogs()` (`6` / `1`), and per-dialog work to `_cleanup_dialog()` (`23` / `1`).
- [x] Refactor `PrivateArchiveService.archive_pm()` into source-fetch, media handling, and export-writing helpers.
  Current delta: `archive_pm()` is down to `37` lines / `1` branch, with stream orchestration moved to `_archive_message_stream()` (`31` / `3`), media handling to `_process_archive_media()` (`20` / `4`), and final UI/reporting to `_emit_archive_complete()` (`27` / `1`).

## Active Refactor Wave

### Block A: Streaming DB Export Path

- [x] A.1 Define a tighter DB export source contract so `DBExportService` can distinguish between materialized messages, row summaries, and iterator factories.
- [x] A.1.1 Remove assumptions that every export source supports `len()` or full in-memory reuse.
- [x] A.1.2 Preserve deterministic fingerprinting and unchanged-export skip semantics across both streaming and materialized sources.
- [x] A.2 Add SQLite read helpers for export summaries and chunked row iteration.
- [x] A.2.1 Keep row ordering deterministic by `(timestamp, message_id)` in both summary and iterator paths.
- [x] A.2.2 Avoid forcing the AI JSON export fast path to preload the entire row set into RAM.
- [x] A.3 Rewire the AI JSON fast path in `DBExportService` to consume rows through iterator factories when the storage backend supports it.
- [x] A.3.1 Keep a compatibility fallback for backends/tests that still only expose materialized `get_user_export_rows()`.
- [x] A.4 Add regression coverage for streaming exports, unchanged-export skipping, and legacy fallback behavior.
  Current delta: AI JSON DB export now prefers `get_user_export_summary()` plus `iter_user_export_rows()` for deterministic streaming writes, `DBExportService` no longer assumes every fast-path source supports `len()`, and legacy materialized-row backends remain supported through the compatibility fallback.

### Block D: Non-Blocking File Writer Path

- [x] D.1 Move async file append work off the event loop thread inside `FileRotateWriter`.
- [x] D.1.1 Keep rotation accounting and persisted state deterministic while writes move to thread-offloaded helpers.
- [x] D.2 Move state persistence in `write_block()` and `finalize()` off the event loop thread.
- [x] D.2.1 Preserve current resume, overwrite, and legacy-state migration behavior.
- [x] D.3 Add regression coverage for the new non-blocking write/persist path.
  Current delta: `FileRotateWriter.write_block()` and `finalize()` now offload file append and state persistence through `asyncio.to_thread()`, while rotation bookkeeping, resume semantics, overwrite cleanup, and legacy-state migration remain unchanged.

### Queued Blocks

- [ ] Block B: Separate service outcomes from terminal rendering so `services/` stop owning direct UI emission.
- [x] Block B.1 Introduce a lightweight service-event sink that can carry progress/status payloads without binding services to terminal rendering.
- [x] Block B.1.1 Keep the sink optional so non-CLI callers and existing tests stay compatible.
- [x] Block B.2 Convert `CleanerService` progress/status output to service events.
- [x] Block B.2.1 Update `cli.py` to render cleaner events through the sink.
- [x] Block B.2.2 Add regression coverage for cleaner event emission.
- [x] Block B.3 Convert `PrivateArchiveService` progress/media/status output to service events.
- [x] Block B.3.1 Update `cli.py` to render PM archive events through the sink.
- [x] Block B.3.2 Add regression coverage for PM archive event emission.
- [ ] Block B.4 Convert `ExportService` progress/header/summary terminal output to service events.
- [ ] Block B.4.1 Keep current CLI behavior intact while moving rendering out of the service.
  Current delta: `CleanerService` and `PrivateArchiveService` now emit typed service events through an optional sink, direct terminal rendering for those flows moved into `cli.py`, and coverage now asserts both service-side event emission and CLI-side sink wiring.
- [ ] Block C: Split the storage contract into smaller read/write/target-oriented interfaces once current service call sites are stable.
