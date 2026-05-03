# TG_CLEANER TODO

## Operating Notes

- Live Telegram session from the project root may be used for validation.
- Live API requests are allowed for read/export and non-destructive chat inspection.
- Avoid ban-risk behavior: respect FloodWait, keep throttling conservative, do not brute-force retries.
- Store all live-test outputs in a separate temporary folder so they do not mix with working exports.
- Current live-test target:
  - `user_id`: `123456789`
  - `chat_id`: `987654321`

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

- [x] Add lint/format/test validation commands.
  Current delta: the repo now ships a `Makefile` with `lint`, `format`, `format-check`, `test`, and `verify`; `pyproject.toml` defines a `dev` extra with `ruff`, local docs point contributors to the shared commands, and CI runs the same `make verify` quality gate used locally.
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

- [x] Block B: Separate service outcomes from terminal rendering so `services/` stop owning direct UI emission.
- [x] Block B.1 Introduce a lightweight service-event sink that can carry progress/status payloads without binding services to terminal rendering.
- [x] Block B.1.1 Keep the sink optional so non-CLI callers and existing tests stay compatible.
- [x] Block B.2 Convert `CleanerService` progress/status output to service events.
- [x] Block B.2.1 Update `cli.py` to render cleaner events through the sink.
- [x] Block B.2.2 Add regression coverage for cleaner event emission.
- [x] Block B.3 Convert `PrivateArchiveService` progress/media/status output to service events.
- [x] Block B.3.1 Update `cli.py` to render PM archive events through the sink.
- [x] Block B.3.2 Add regression coverage for PM archive event emission.
- [x] Block B.4 Convert `ExportService` progress/header/summary terminal output to service events.
- [x] Block B.4.1 Convert `sync_chat()` header/progress/final-summary output to service events.
- [x] Block B.4.1.1 Keep current CLI behavior intact while moving single-chat rendering out of the service.
- [x] Block B.4.1.2 Add regression coverage for `sync_chat()` event emission.
- [x] Block B.4.2 Convert bulk dialog search/update output in `sync_all_dialogs_for_user()` and `_sync_target_items()` to service events.
- [x] Block B.4.2.1 Keep current CLI behavior intact while moving bulk-flow rendering out of the service.
- [x] Block B.4.2.2 Add regression coverage for bulk export/update event emission.
  Current delta: `CleanerService`, `PrivateArchiveService`, and all currently user-facing `ExportService` flows now emit typed service events through an optional sink; direct terminal rendering for those flows moved into `cli.py`, and coverage asserts both service-side event emission and CLI-side sink wiring.
- [x] Block C: Split the storage contract into smaller read/write/target-oriented interfaces once current service call sites are stable.
- [x] Block C.1 Introduce narrow read/write/lifecycle storage protocols alongside the legacy umbrella contract.
- [x] Block C.1.1 Bring the umbrella `BaseStorage` back in sync with the real SQLite API so it no longer omits sync-control/export helpers.
- [x] Block C.2 Re-type each service against the smallest storage contract it actually consumes.
- [x] Block C.2.1 Keep runtime behavior unchanged by using structural typing instead of rewriting `SQLiteStorage`.
- [x] Block C.3 Add regression coverage that `SQLiteStorage` satisfies the service-specific runtime protocols.
  Current delta: `interface.py` now exposes focused protocols such as `CleanerStorage`, `ContextStorage`, `DBExportStorage`, `PrivateArchiveStorage`, and `ExportStorage`; service constructors depend on those narrower contracts instead of the monolithic storage type, while `SQLiteStorage` remains a compatible umbrella backend and is verified against the new runtime-checkable protocols.

## Phase 9: Runtime Bootstrap And Path Injection

- [x] Remove the package-level `settings` singleton from the main execution path and bootstrap runtime state explicitly in CLI entrypoints.
- [x] Introduce `AppRuntime` / `AppPaths` so project root, DB path, lock path, export dirs, and Python executable live in one composition object.
- [x] Inject runtime settings and paths into `CLIContext`, `TelethonClientWrapper`, `DBExportService`, `PrivateArchiveService`, and `CleanerService`.
- [x] Remove `cwd` / `./.venv-test` assumptions from scheduler and alias setup flows.
- [x] Add regression coverage for runtime path resolution and runtime-aware CLI initialization.
  Current delta: `cli.py` now builds an explicit `AppRuntime`, `core/runtime.py` centralizes path resolution, relative DB/config paths are resolved from a declared project root, `CleanerService.purge_user_data()` scans injected artifact roots instead of hardcoded directories, `DBExportService` and `PrivateArchiveService` receive explicit output roots, and alias/scheduler setup now use the active runtime executable instead of a baked-in venv path.

## Phase 10: CLI Presentation Extraction

- [x] Move raw TTY input handling out of `cli.py` into a dedicated CLI I/O module.
- [x] Move service-event rendering out of `cli.py` while preserving the existing terminal behavior.
- [x] Move target-list, update-summary, pause, and main-menu rendering helpers out of `cli.py`.
- [x] Re-run CLI and service tests after the extraction to keep behavior stable.
  Current delta: `tg_msg_manager/cli_io.py` now owns terminal input and all extracted presentation helpers, while `cli.py` stays focused on runtime wiring and command/menu orchestration instead of mixing that with low-level rendering.

## Phase 11: Typed Storage Read Records

- [x] Introduce typed read-side storage records for sync status, tracked targets, sync users, and export summaries.
- [x] Keep record instances backward-compatible with existing `dict`-style access during the migration window.
- [x] Convert SQLite read-path methods to return typed records instead of raw `dict` payloads.
- [x] Update `ExportService`, `DBExportService`, and CLI target rendering to consume typed attributes on the hot paths.
- [x] Add regression coverage for typed record returns while preserving legacy index access in tests.
  Current delta: storage read models now flow through `SyncStatus`, `PrimaryTarget`, `SyncUser`, and `UserExportSummary` in `infrastructure/storage/records.py`; SQLite and the main export/CLI paths consume typed attributes, while `__getitem__`/`get()` compatibility keeps older tests and mocks working during the transition.

## Phase 12: Named Service Events And Renderer Registry

- [x] Introduce named service-event constants instead of duplicating raw event-name strings across services and CLI rendering.
- [x] Convert exporter, cleaner, and private-archive services to emit those named events.
- [x] Replace the monolithic `render_service_event()` conditional chain with an event-to-renderer registry.
- [x] Re-run event-heavy service and sync tests to confirm the refactor preserved emitted event names and CLI behavior.
  Current delta: `core/service_events.py` now owns `ExportEvents`, `CleanerEvents`, and `PrivateArchiveEvents`, service emitters reference those constants directly, and `cli_io.py` routes events through a renderer registry instead of a long sequence of string comparisons.

## Phase 13: Typed Export Sync Context

- [x] Replace the internal `sync_chat()` prep context `dict` with a dedicated dataclass so checkpoint, mode, and header state travel together.
- [x] Keep the external behavior and emitted payloads unchanged while removing internal string-key lookups from the hot sync path.
- [x] Re-run exporter and tracked-sync tests after the context conversion.
  Current delta: `ExportService._prepare_sync_target()` now returns a `_SyncTargetContext` dataclass instead of a loose mapping, which trims internal key-string plumbing in `sync_chat()` without changing the public service API or event payload shape.

## Phase 14: Context-Local I18N Runtime

- [x] Replace module-global language state with a context-local language holder so concurrent tasks stop sharing one mutable locale flag.
- [x] Add a normalized `lang` setting with legacy aliases so runtime language can be declared in config/env without extra glue code.
- [x] Bind CLI entrypoints to the runtime language context before parser/help rendering and command execution.
- [x] Add regression coverage for language normalization, context restoration, task-local isolation, and runtime-to-CLI language propagation.
  Current delta: `i18n.py` now uses a `ContextVar` plus `use_lang()` instead of a plain module global, `Settings` accepts `lang` / `language` / `ui_language`, and `run_cli()` / `main_menu()` execute inside the runtime language scope so parser/help strings and handlers stay locale-consistent per invocation.

## Phase 15: Typed Tracked Sync Report Stats

- [x] Replace loose `user_stats` dict payloads in tracked sync flows with a typed per-user report object.
- [x] Keep CLI summary rendering and dirty-target filtering backward-compatible during the transition by coercing legacy dict-shaped mocks.
- [x] Re-run tracked-sync and CLI tests after the report-object conversion.
  Current delta: tracked update summaries now flow through `TrackedSyncUserStat` in `core/models/sync_report.py`; `ExportService`, `get_dirty_target_ids()`, and `print_update_summary()` use typed attributes internally while preserving legacy index access for existing tests and mocks.

## Phase 16: Typed Export Event Payloads

- [x] Replace string-oriented `sync_chat_started` payload construction in `ExportService` with a typed DTO that carries semantic fields instead of pre-rendered UI strings.
- [x] Move mode/status text rendering for export-start events fully into `cli_io.py` so localization stays on the presentation side.
- [x] Replace loose sync-summary payload assembly with a typed DTO and validate the payload shape in service tests.
- [x] Re-run export service and tracked-sync tests after the event-payload conversion.
  Current delta: `ExportService` now emits `ExportSyncStartedPayload` and `ExportSyncSummaryPayload` from `core/models/service_payloads.py`; `cli_io.py` derives localized badges/text from semantic fields like `deep_mode`, `depth`, and `status_kind`, so the service layer no longer injects translated `mode_str` / `status_str` strings into event payloads.

## Phase 17: Structured Setup And PM Archive Results

- [x] Replace `AliasManager.install()` stringly/localized result dicts with a structured install result model.
- [x] Move alias success/error/help text rendering fully into CLI code so `AliasManager` stops depending on `_()` directly.
- [x] Replace loose PM archive context/event payload dict assembly with typed models where the service was still passing raw mappings around.
- [x] Add regression coverage for structured alias-install results and typed PM archive event payloads.
  Current delta: `AliasManager` now returns `AliasInstallResult` / `AliasHelpEntry` from `core/models/setup.py` instead of localized dict blobs, CLI setup rendering owns the translation step, `PrivateArchiveService` uses a typed `_ArchiveContext` plus typed event DTOs from `core/models/service_payloads.py`, and tests cover both the new alias result contract and PM archive payload shapes.

## Phase 18: Structured Scheduler Setup Flow

- [x] Split scheduler setup into a typed request/result contract so the service stops reading input and printing terminal output directly.
- [x] Move schedule prompt parsing and success/error rendering into CLI handlers.
- [x] Add scheduler executor tests for plist generation, launchctl failure handling, and request validation.
- [x] Add CLI wiring coverage that `schedule` passes a typed request into the scheduler service.
  Current delta: `services/scheduler.py` now takes `SchedulerSetupRequest` and returns `SchedulerSetupResult` from `core/models/setup.py`, scheduler side effects are wrapped behind a pure executor boundary, and CLI owns both prompt parsing and localized result rendering for `schedule`.

## Phase 19: Typed Bulk Event Rendering Contracts

- [x] Add typed payload DTOs for the remaining bulk export, sync progress/finish, and cleaner dialog events that `cli_io.py` still parsed as raw dicts.
- [x] Convert `ExportService` and `CleanerService` emitters to construct those DTOs before firing service events.
- [x] Convert `cli_io.py` renderers to coerce typed payloads instead of indexing untyped dicts.
- [x] Extend cleaner and sync-system tests to validate the new payload shapes on emitted events.
  Current delta: the remaining bulk/event-rendering hotspots now flow through typed payloads in `core/models/service_payloads.py` such as `ExportSyncProgressPayload`, `ExportDialogScanStartedPayload`, `ExportTrackedUpdateStartedPayload`, and `CleanerDialogMessagesFoundPayload`; `cli_io.py` no longer manually unpacks those event dicts, and the corresponding cleaner/bulk-sync tests assert the typed contracts.

## Phase 20: Typed Export Scan State

- [x] Replace internal scan-range dicts in `ExportService` with dedicated typed range objects.
- [x] Replace per-range scan result dicts with a typed result contract and keep a narrow coercion shim for legacy tests.
- [x] Replace shared sync progress counters with a typed progress-state object instead of a mutable string-key dict.
- [x] Re-run exporter and sync-system coverage after the scan-state conversion.
  Current delta: `ExportService` now threads `_ScanRange`, `_ScanRangeResult`, and `_SyncProgressStats` through `sync_chat()` and its worker helpers, which removes the remaining `\"upper\"` / `\"lower\"` / `\"linked\"` string-key plumbing from the hot scan path while preserving checkpoint behavior and legacy unit-test compatibility at the private coercion boundary.

## Phase 21: Typed Tracked Sync Run Report

- [x] Replace bare tracked-sync result dicts with a dedicated report object that owns per-user stats.
- [x] Keep CLI helpers and tests compatible by giving the report a map-like surface plus coercion from legacy dict payloads.
- [x] Update `ExportService.sync_all_tracked()` / `sync_all_outdated()` and summary helpers to speak the typed report contract.
- [x] Re-run CLI and tracked-sync tests after the report-object conversion.
  Current delta: tracked bulk-update flows now return `TrackedSyncRunReport` from `core/models/sync_report.py` instead of a raw `dict`; the report owns dirty-target filtering and total-processed aggregation, while `cli.py`, `cli_io.py`, and older tests remain compatible through the report's coercion and mapping-style accessors.

## Phase 22: Typed Private Archive Stats

- [x] Replace PM archive media and transfer counter dicts with dedicated typed stats models.
- [x] Update private-archive payload DTOs to carry typed stats instead of nested raw mappings.
- [x] Move CLI archive summaries off string-key dict indexing onto typed attributes while preserving payload coercion compatibility.
- [x] Re-run PM archive service coverage after the stats-model conversion.
  Current delta: `PrivateArchiveMediaStats` and `PrivateArchiveTransferStats` now back the PM archive flow in `core/models/service_payloads.py`, `services/private_archive.py` mutates typed counters directly, and `cli_io.py` renders archive progress/final summaries from typed attributes rather than `\"Photo\"` / `\"downloaded\"` key lookups.

## Phase 23: Typed User Metadata And Export Rows

- [x] Replace raw `get_user()` dict payloads with a dedicated stored-user record.
- [x] Replace export-row iterator/materialization payloads with a typed row record while keeping mapping-style compatibility for legacy code.
- [x] Rewire SQLite read-path interfaces and `DBExportService` to coerce legacy backends onto the new typed records.
- [x] Re-run storage and export-adjacent tests after the record conversion.
  Current delta: `StoredUser` and `UserExportRow` now live in `infrastructure/storage/records.py`, `UserReadStorage` advertises typed user/export-row contracts, SQLite read helpers return those records directly, and `DBExportService` consumes typed rows while still accepting legacy dict-shaped backends through coercion wrappers.

## Phase 24: Typed Breakdown And Purge Results

- [x] Replace linked-message breakdown dicts with a dedicated typed record on the storage read path.
- [x] Replace `delete_user_data()` tuple returns with a typed purge result while keeping tuple coercion compatibility in services.
- [x] Update `ExportService` and `CleanerService` to consume those typed results without breaking legacy mocks.
- [x] Re-run storage, exporter, and cleaner coverage after the contract conversion.
  Current delta: `TargetMessageBreakdown` and `DeleteUserDataResult` now live in `infrastructure/storage/records.py`, SQLite returns those records directly for breakdown/purge calls, `ExportService` coerces breakdowns before summary emission, and `CleanerService` now works against a typed purge result while remaining compatible with older tuple-shaped storage mocks.

## Phase 25: Typed Maintenance Records

- [x] Replace terminal-repair result dicts with a dedicated typed maintenance record.
- [x] Replace retry-queue read results with typed retry-task records.
- [x] Keep migration-friendly mapping-style access for existing tests while tightening the SQLite maintenance API.
- [x] Re-run storage and concurrency coverage after the maintenance-record conversion.
  Current delta: `TerminalRepairCandidate` and `RetryTaskRecord` now live in `infrastructure/storage/records.py`, SQLite maintenance helpers return those records directly, and the storage/concurrency tests now assert typed maintenance payloads instead of only raw DB rows.
