import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "messages.db"
DEFAULT_EXPORT_DIR = ROOT / "DB_EXPORTS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export all stored messages of a user plus the messages directly linked "
            "to them inside the same chat."
        )
    )
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument(
        "--chat-id",
        type=int,
        default=None,
        help="Limit export to one chat. By default scans all chats in the DB.",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to SQLite database. Default: %(default)s",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "txt"),
        default="jsonl",
        help="Output format. Default: %(default)s",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional explicit output path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for smoke checks.",
    )
    return parser.parse_args()


def resolve_output_path(
    *,
    user_id: int,
    chat_id: int | None,
    fmt: str,
    output: str | None,
) -> Path:
    if output:
        return Path(output).expanduser().resolve()

    suffix = f"_chat_{chat_id}" if chat_id is not None else ""
    return (
        DEFAULT_EXPORT_DIR
        / f"context_user_{user_id}{suffix}.{ 'jsonl' if fmt == 'jsonl' else 'txt' }"
    )


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_related_messages(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    chat_id: int | None,
    limit: int | None,
) -> list[sqlite3.Row]:
    params: dict[str, Any] = {"user_id": user_id}
    chat_filter = ""
    if chat_id is not None:
        chat_filter = "AND user_id = :user_id AND chat_id = :chat_id"
        params["chat_id"] = chat_id
    else:
        chat_filter = "AND user_id = :user_id"

    limit_clause = ""
    if limit is not None and limit > 0:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit

    query = f"""
        WITH target_messages AS (
            SELECT
                chat_id,
                message_id,
                reply_to_id,
                context_group_id
            FROM messages
            WHERE 1 = 1
            {chat_filter}
        ),
        related_candidates AS (
            SELECT
                t.chat_id,
                t.message_id,
                'author' AS relation_reason,
                t.message_id AS anchor_message_id
            FROM target_messages t

            UNION ALL

            SELECT
                m.chat_id,
                m.message_id,
                'replies_to_user' AS relation_reason,
                t.message_id AS anchor_message_id
            FROM messages m
            JOIN target_messages t
              ON m.chat_id = t.chat_id
             AND m.reply_to_id = t.message_id

            UNION ALL

            SELECT
                m.chat_id,
                m.message_id,
                'replied_by_user' AS relation_reason,
                t.message_id AS anchor_message_id
            FROM messages m
            JOIN target_messages t
              ON m.chat_id = t.chat_id
             AND m.message_id = t.reply_to_id
            WHERE t.reply_to_id IS NOT NULL

            UNION ALL

            SELECT
                m.chat_id,
                m.message_id,
                'shared_context_group' AS relation_reason,
                t.message_id AS anchor_message_id
            FROM messages m
            JOIN target_messages t
              ON m.chat_id = t.chat_id
             AND m.context_group_id = t.context_group_id
            WHERE t.context_group_id IS NOT NULL
              AND TRIM(t.context_group_id) != ''
        ),
        aggregated_relations AS (
            SELECT
                chat_id,
                message_id,
                GROUP_CONCAT(DISTINCT relation_reason) AS relation_reasons,
                MIN(anchor_message_id) AS first_anchor_message_id
            FROM related_candidates
            GROUP BY chat_id, message_id
        )
        SELECT
            m.chat_id,
            COALESCE(c.title, '') AS chat_title,
            m.message_id,
            m.user_id,
            COALESCE(m.author_name, '') AS author_name,
            m.timestamp,
            COALESCE(m.text, '') AS text,
            COALESCE(m.media_type, '') AS media_type,
            m.reply_to_id,
            m.fwd_from_id,
            COALESCE(m.context_group_id, '') AS context_group_id,
            COALESCE(ar.relation_reasons, '') AS relation_reasons,
            ar.first_anchor_message_id
        FROM aggregated_relations ar
        JOIN messages m
          ON m.chat_id = ar.chat_id
         AND m.message_id = ar.message_id
        LEFT JOIN chats c
          ON c.chat_id = m.chat_id
        ORDER BY m.chat_id ASC, m.timestamp ASC, m.message_id ASC
        {limit_clause}
    """
    return conn.execute(query, params).fetchall()


def format_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def row_to_payload(row: sqlite3.Row, target_user_id: int) -> dict[str, Any]:
    reasons = [part for part in row["relation_reasons"].split(",") if part]
    return {
        "chat_id": row["chat_id"],
        "chat_title": row["chat_title"] or None,
        "message_id": row["message_id"],
        "user_id": row["user_id"],
        "author_name": row["author_name"] or None,
        "timestamp": row["timestamp"],
        "timestamp_iso": format_timestamp(row["timestamp"]),
        "text": row["text"] or None,
        "media_type": row["media_type"] or None,
        "reply_to_id": row["reply_to_id"],
        "fwd_from_id": row["fwd_from_id"],
        "context_group_id": row["context_group_id"] or None,
        "relation_reasons": reasons,
        "anchor_message_id": row["first_anchor_message_id"],
        "is_user_message": row["user_id"] == target_user_id,
    }


def write_jsonl(rows: list[sqlite3.Row], output_path: Path, target_user_id: int) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = row_to_payload(row, target_user_id)
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def write_txt(rows: list[sqlite3.Row], output_path: Path, target_user_id: int) -> None:
    grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[row["chat_id"]].append(row)

    with output_path.open("w", encoding="utf-8") as handle:
        for chat_id, chat_rows in grouped.items():
            chat_title = chat_rows[0]["chat_title"] or "Unknown chat"
            handle.write(f"=== Chat: {chat_title} ({chat_id}) ===\n\n")

            for row in chat_rows:
                reasons = row["relation_reasons"] or ""
                author_name = row["author_name"] or f"User_{row['user_id']}"
                role = "USER" if row["user_id"] == target_user_id else "CONTEXT"
                reply_part = (
                    f" | reply_to={row['reply_to_id']}" if row["reply_to_id"] else ""
                )
                media_part = (
                    f" | media={row['media_type']}" if row["media_type"] else ""
                )
                cluster_part = (
                    f" | context_group={row['context_group_id']}"
                    if row["context_group_id"]
                    else ""
                )
                handle.write(
                    f"[{format_timestamp(row['timestamp'])}] "
                    f"<{author_name} ({row['user_id']})> "
                    f"[{role}] [reasons={reasons}]{reply_part}{media_part}{cluster_part}\n"
                )
                handle.write(f"{row['text'] or '(empty)'}\n\n")


def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve()
    output_path = resolve_output_path(
        user_id=args.user_id,
        chat_id=args.chat_id,
        fmt=args.format,
        output=args.output,
    )

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect_db(db_path)
    try:
        rows = fetch_related_messages(
            conn,
            user_id=args.user_id,
            chat_id=args.chat_id,
            limit=args.limit,
        )
    finally:
        conn.close()

    if not rows:
        print("No matching messages found in the DB.")
        return 2

    if args.format == "jsonl":
        write_jsonl(rows, output_path, args.user_id)
    else:
        write_txt(rows, output_path, args.user_id)

    own_count = sum(1 for row in rows if row["user_id"] == args.user_id)
    context_count = len(rows) - own_count
    print(f"Saved: {output_path}")
    print(f"Rows: {len(rows)}")
    print(f"User messages: {own_count}")
    print(f"Direct context messages: {context_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
