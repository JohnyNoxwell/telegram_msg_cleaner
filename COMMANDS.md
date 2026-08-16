# Commands

First-run navigation: [`docs/user/QUICKSTART.md`](docs/user/QUICKSTART.md)
Documentation map: [`docs/README.md`](docs/README.md)
Coding-agent contract: [`AGENTS.md`](AGENTS.md)

## `export`

Sync user/group messages and write a final local export artifact.

Examples:

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --txt-profile context-readable
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --txt-profile legacy
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --json
```

Arguments:

- `--user-id` required. Target user ID or username accepted by the current resolver.
- `--chat-id` optional. Restrict sync to one chat.
- `--deep` / `--flat` controls context collection mode; default is deep mode.
- `--context-window`, `--max-cluster`, `--depth`, and `--limit` keep their existing sync meanings.
- For `export`, `--limit` is passed to each `sync_chat` call. With `--chat-id`
  it caps that one dialog; without `--chat-id`, a multi-dialog user export
  applies the cap separately per dialog, not as one global user total.
- `--json` writes JSONL instead of TXT.
- `--txt-profile` optional for TXT output. Values: `context-readable`, `legacy`. Default for `export` TXT is `context-readable`.

TXT profiles:

- `context-readable` is the default human-readable projection for user/group export. It renders `CONTEXT BLOCK` sections with `[REPLIED MESSAGE]`, `[CONTEXT BEFORE]`, `[TARGET MESSAGE]` / `[TARGET MESSAGES]`, and `[CONTEXT AFTER]`.
- Missing replies render compactly as `↪ missing reply #id`.
- `legacy` keeps the old flat log-style TXT shape for compatibility.
- TXT is a projection only. JSONL/database records remain canonical.
- `db-export` also supports these TXT profiles and defaults to `context-readable`.

## `db-export`

Export cached SQLite messages for one user into TXT or JSONL.

Examples:

```bash
python3 -m tg_msg_manager.cli db-export --user-id 123456789
python3 -m tg_msg_manager.cli db-export --user-id 123456789 --txt-profile context-readable
python3 -m tg_msg_manager.cli db-export --user-id 123456789 --txt-profile legacy
python3 -m tg_msg_manager.cli db-export --user-id 123456789 --json
```

Arguments:

- `--user-id` required. Target user ID.
- `--json` optional. Write compact AI-friendly JSONL instead of TXT.
- `--txt-profile` optional for TXT output. Values: `context-readable`, `legacy`. Default for DB TXT export is `context-readable`.

Notes:

- `context-readable` renders the same readable context-block markers as regular TXT export when context is present.
- `legacy` keeps the old flat log-style TXT shape for compatibility.
- JSONL behavior is unchanged by `--txt-profile`.

## `export-pm`

Create a text-and-media private-dialog archive for one user.

Example:

```bash
python3 -m tg_msg_manager.cli export-pm --user-id 123456789
```

Notes:

- `export-pm` is a separate archive workflow, not part of the user/group
  `export` plus `db-export` Non-Channel Export Contract V1.
- The private archive public contract is deferred. Current output should be
  treated as a practical local archive, not a stable replayable Telegram
  dataset contract.

## `export-channel`

Export posts directly from a Telegram channel into a filesystem dataset.

Example:

```bash
python3 -m tg_msg_manager.cli export-channel --channel @example --limit 100 --media metadata
python3 -m tg_msg_manager.cli export-channel --channel @example --limit 100 --media full
python3 -m tg_msg_manager.cli export-channel --channel @example --limit 100 --media full --max-media-size 50MB --media-types photo,video
python3 -m tg_msg_manager.cli export-channel --channel @example --limit 10 --media metadata --discussion full --max-comments-per-post 100
```

Arguments:

- `--channel` required. Broadcast-channel username, numeric ID, or another value accepted by `get_entity`.
- `--limit` optional. Maximum number of posts to export.
- `--media` optional. `none`, `metadata`, or `full`.
- `--max-media-size` optional. Maximum file size for `--media full`. Accepts bytes or units such as `50MB`. Default in full mode: `50MB`.
- `--media-types` optional. Comma-separated allowlist for `--media full`: `photo`, `video`, `document`, `audio`, `voice`, `animation`.
- `--discussion` optional. `none`, `metadata`, or `full`. Default: `none`.
- `--max-comments-per-post` optional. Positive integer limit for linked discussion comments per exported channel post. Default: `100`.
- `--output-dir` optional. Base directory for channel export datasets.
- `--force` optional. Ignore `channel_export_state.json`, rebuild the dataset from scratch, and recreate state.

Dataset layout:

```text
exports/
  channels/
    @channel_name__123456789/
      manifest.json
      messages.jsonl
      messages.txt
      media_manifest.jsonl
      run_changelog.jsonl
      channel_export_state.json
      media/
      discussion_metadata.jsonl       # only with --discussion metadata
      discussion_comments.jsonl       # only with --discussion full
      discussion_comments.txt         # only with --discussion full
      discussion_threads.jsonl        # only with --discussion full
      discussion_export_state.json    # only with --discussion full
```

Notes:

- Stage 3A / 3A.1 / 3B / 3C is dataset projection only. No analytics are performed.
- `export-channel` accepts broadcast channels only. Groups and supergroups are not supported.
- Default media mode is `metadata`.
- Default discussion mode is `none`; in this mode no discussion resolver runs, no comments are fetched, and no discussion files are written.
- `--discussion metadata` writes compact post-level discussion metadata to `discussion_metadata.jsonl` from `raw_payload.replies` and does not fetch comments.
- `--discussion full` is explicit heavy mode and exports linked discussion comments only for channel posts fetched in the current run. For large channels it can produce millions of records and multi-gigabyte datasets; prefer `metadata` for broad archives.
- Discussion resolution uses channel linked-discussion metadata first, then falls back to per-post Telegram metadata (`raw_payload.replies.channel_id`) when the channel-level link is unavailable.
- Incremental runs export discussions only for newly fetched posts. No-new-posts runs do not refetch old discussion threads and do not mutate `discussion_export_state.json`.
- `--force --discussion full` overwrites discussion files and rebuilds discussion state for posts fetched in that force run.
- Existing datasets that were exported before discussion fallback support may need `--force --discussion full` or a clean output directory to reprocess old threads.
- `--media full` downloads files only when explicitly requested and records final statuses in `media_manifest.jsonl`.
- Media filenames and final media subdirectories are resolved from a safe Telegram original filename, then Telegram MIME type, then lightweight magic bytes. `.bin` is used only when the type remains unknown.
- `media_manifest.jsonl` records the final media path; no OCR, speech-to-text, media analysis, transcoding, or ffmpeg processing is performed.
- Full media statuses are `downloaded`, `already_exists`, `skipped_by_size`, `skipped_by_type`, and `failed`.
- Discussion comment media remains metadata-only; full media download for discussion comments is not implemented.
- Discussion comments are not persisted to SQLite, and no SQLite migration is required.
- Successful runs create/update `channel_export_state.json` with the last exported message id and aggregate counters.
- A second run without `--force` exports only posts newer than `last_exported_message_id` and appends to `messages.jsonl`, `messages.txt`, and `media_manifest.jsonl`.
- Every completed run appends one summary row to `run_changelog.jsonl` with previous/new cursor, new message ids, date range, run mode, and artifact paths. No-new-posts runs append a row with `new_message_count: 0`.
- Channel and discussion payload appends use temp-file copy/append/replace, so a write-session failure does not partially append final payload files.
- `channel_export_state.json` and `discussion_export_state.json` advance only after required payload and manifest writes succeed.
- If there are no new posts, the command reports that state clearly and does not advance the export cursor.

## `update-channels`

Incrementally update every existing broadcast-channel dataset under one export root.

```bash
python3 -m tg_msg_manager.cli update-channels
python3 -m tg_msg_manager.cli update-channels --output-dir /path/to/channels
```

- `--output-dir` is optional and defaults to the normal channel export root.
- Immediate child directories containing `channel_export_state.json` or `manifest.json` are processed in sorted order; unrelated directories are ignored.
- Each valid dataset reuses its committed media, discussion, and JSONL/TXT settings and delegates to the existing `export-channel` incremental path with `force=False` and no message limit.
- For batch-read compatibility, legacy manifests with missing or null `discussion` are treated as `discussion.mode=none`; the source manifest is not rewritten. Other non-object discussion values remain invalid.
- Processing is sequential. Invalid datasets and per-channel Telegram/export failures are reported without stopping later channels.
- The command prints `updated`, `no_new_posts`, and `failed` totals and exits non-zero after all candidates are processed when any candidate failed.
- For channels without a username, the stored numeric channel ID is used. Private channels still depend on Telegram being able to resolve that ID from the current session/entity cache.
- The command does not backfill historical media or discussion threads and does not change dataset or SQLite schemas.

## `validate-dataset`

Validate a completed channel export dataset from local files only.

Examples:

```bash
python3 -m tg_msg_manager.cli validate-dataset --path exports/channels/example
python3 -m tg_msg_manager.cli validate-dataset --path exports/channels/example --json
```

Arguments:

- `--path` required. Path to an exported channel dataset directory.
- `--json` optional. Emit deterministic JSON instead of the default Markdown report.

Notes:

- The command is read-only and does not require Telegram credentials or a Telegram client connection.
- Validation checks required files, JSON/JSONL parseability, duplicate post ids, message-id gaps, reply links where exported fields are available, manifest/state counter sanity, media manifest ids/paths/statuses, `run_changelog.jsonl`, and mode-specific discussion files declared by the manifest.
- Message-id gaps and missing reply parents are warnings by default because Telegram deletions, unavailable parents, and scoped exports can produce the same local shape.
- Status values are `ok`, `warnings`, and `errors`.
- `errors` exits with code `1`; warnings do not fail the command.
- The command does not repair, migrate, fetch, analyze content, OCR, STT, optimize media, or write SQLite data.

## `inspect-dataset`

Inspect deterministic counts and statuses for a completed channel export dataset.

Examples:

```bash
python3 -m tg_msg_manager.cli inspect-dataset --path exports/channels/example
python3 -m tg_msg_manager.cli inspect-dataset --path exports/channels/example --json
python3 -m tg_msg_manager.cli inspect-dataset --path exports/channels/example --doctor
python3 -m tg_msg_manager.cli inspect-dataset --path exports/channels/example --doctor --json
```

Arguments:

- `--path` required. Path to an exported channel dataset directory.
- `--json` optional. Emit deterministic JSON instead of the default Markdown report.
- `--doctor` optional. Emit a read-only doctor report with severity, artifact path, message, and suggested next action for each validation finding.

Notes:

- The command is read-only and does not require Telegram credentials or a Telegram client connection.
- Inspection summarizes detected files, message counts, media status counts, discussion presence/counts, manifest summary, state cursor, and validation note counts.
- Doctor mode reuses validation findings and adds deterministic remediation guidance without repairing or rewriting files.
- Inspection does not interpret message/comment text or perform analytics.
- Synthetic doctor examples are documented in [`docs/user/DATASET_DOCTOR_EXAMPLES.md`](docs/user/DATASET_DOCTOR_EXAMPLES.md).

## `target names`

Show locally stored username/display name/title history for a known target.

Examples:

```bash
python3 -m tg_msg_manager.cli target names 123456789
python3 -m tg_msg_manager.cli target names 123456789 --field username
python3 -m tg_msg_manager.cli target names -1001234567890 --field title --format json
```

Arguments:

- `<target>` required. Numeric user/chat/channel id or locally stored username.
- `--field` optional. Values: `all`, `username`, `display_name`, `title`. Default: `all`.
- `--format` optional. Values: `text`, `json`. Default: `text`.

Notes:

- The command reads local SQLite metadata only. It does not connect to Telegram,
  refresh entity data, write SQLite data, or change export artifacts.
- History can be incomplete if the target was not observed by earlier local
  sync/export work.
- Text output renders timestamps as local `YYYY-MM-DD HH:MM:SS`; JSON output
  keeps raw epoch seconds.
- Chat/channel title history is not stored in the current SQLite schema; known
  chat/channel targets show current title with empty title history.
- Output is stored metadata facts only, not identity, profiling, OSINT, or
  behavioral analysis.

## `clean`

Delete messages authored by the current Telegram account from eligible groups
and channels.

Examples:

```bash
python3 -m tg_msg_manager.cli clean --dry-run
python3 -m tg_msg_manager.cli clean --apply --yes
```

Notes:

- Live cleanup removes matching messages from Telegram but preserves existing
  SQLite message rows and target-context links for later local exports.
- Dry-run does not delete Telegram or SQLite data.
- Private dialogs are excluded from the direct CLI cleanup path, and whitelist
  rules remain in effect.

## Interactive Menu

The interactive `tg` menu uses this ordered two-digit mapping:

- exports: `01` user export, `02` PM archive, `03` DB export, `04` channel export;
- updates: `05` tracked-target update, `06` channel-export update, `07` Retry Queue;
- maintenance/settings: `08` global clean, `09` delete data, `10` scheduler, `11` setup;
- information: `12` Audit Report, `13` About;
- `98` for language toggle
- `00` for exit

Legacy short inputs remain accepted for compatibility:

- `1`..`9` as short forms of the current two-digit mapping
- `R`
- `P`
- `L`
- `0`

Interactive menu item `04` / `export-channel` asks for the same channel export
controls as the direct command path: discussion mode (`none` / `metadata` /
`full`), max comments per post, force re-export, output directory, max media
size, and media types. Empty answers preserve the direct CLI defaults.

Interactive menu item `06` invokes `update-channels` with the default channel
export root. It renders the complete per-channel summary, remains in the menu
after aggregate failures, and does not add force/backfill behavior.

Interactive menu item `01` / `export` can generate TXT output and prompts for
the same TXT profile behavior when TXT is selected. Empty TXT profile input uses
`context-readable`; `legacy` remains available explicitly.

## `schedule`

Register the built-in background `update` scheduler.

Example:

```bash
python3 -m tg_msg_manager.cli schedule
```

Notes:

- The current scheduler implementation targets macOS `launchd` / `launchctl`
  and writes a LaunchAgent plist for `python -m tg_msg_manager.cli update`.
- Non-macOS behavior is not a supported scheduler path in the current command.

## Entrypoints

Supported local entrypoints delegate to the same CLI main function:

```bash
python3 run.py
python3 -m tg_msg_manager.cli
tg-msg-manager
```

`tg-msg-manager` is the installed console script from package metadata.
