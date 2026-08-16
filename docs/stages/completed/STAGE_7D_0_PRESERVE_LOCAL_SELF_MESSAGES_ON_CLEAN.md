# Stage 7D.0 — Preserve Local Self Messages On Clean

Status: completed
Type: behavior change
Depends on: none

## CODEX ENTRY CONTRACT

Read `AGENTS.md`, this file, `docs/architecture/ARCHITECTURE_RULES.md`, and
`docs/development/PR_CHECKLIST.md`. Implement only this stage.

## PURPOSE

Keep locally stored messages unchanged when `clean --apply` removes the
current account's messages from Telegram.

## FILES TO INSPECT

- `tg_msg_manager/services/cleaner.py`
- `tests/services/cleaner/test_cleaner.py`
- `COMMANDS.md`
- `deploy/vps/README.md`
- `.github/workflows/ci.yml`

Do not inspect unrelated source, archive, roadmap, reports, or completed stages.

## HARD PROHIBITIONS

- No CLI name, argument, default, or output changes.
- No SQLite schema, migration, or storage-contract changes.
- No target synchronization, export, or explicit `delete --user-id` changes.
- No protected facade or compatibility-wrapper changes.
- No dependency additions, broad refactors, unrelated cleanup, or formatting churn.

## ATOMIC IMPLEMENTATION TASKS

1. Confirm the current live-clean path and SQLite deletion call; do not edit yet.
2. Remove only the local SQLite deletion from successful Telegram cleanup.
3. Replace the deletion expectation with regression coverage for local retention.
4. Update only the cleanup behavior notes in required docs.

## REQUIRED DOCS

- `COMMANDS.md`
- `deploy/vps/README.md`
- Report: `docs/stages/reports/STAGE_7D_0_PRESERVE_LOCAL_SELF_MESSAGES_ON_CLEAN_REPORT.md`

## TESTS / VERIFICATION

```bash
python3 -m pytest tests/services/cleaner/test_cleaner.py -q
make verify
make pre-commit
```

Do not claim a check passed unless it was run successfully. A tooling failure
leaves the stage incomplete.

## REPORT

Write a factual Russian report with scope, changed files, checks, preserved
contracts, and architecture-guard verdict.

## COMPLETION CRITERIA

- Telegram cleanup succeeds while matching SQLite rows and target links remain.
- Focused regression coverage and required docs are updated.
- Required checks pass and the factual report exists.
- Move this file to `docs/stages/completed/` and update `docs/stages/README.md`.

## OUTPUT LIMITS

Follow the compact final format and limits from `AGENTS.md`. Do not include a
full diff, broad summary, or unrelated recommendations.
