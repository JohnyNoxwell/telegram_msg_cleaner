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
