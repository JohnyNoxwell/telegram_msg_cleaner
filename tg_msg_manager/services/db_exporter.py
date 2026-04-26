import os
import re
import glob
import json
import logging
from dataclasses import dataclass
from time import perf_counter
from datetime import datetime
from typing import Any, Dict, List, Optional
from .file_writer import FileRotateWriter
from ..infrastructure.storage.interface import BaseStorage
from ..core.models.message import MessageData
from ..core.telemetry import telemetry
from ..utils.ui import UI

logger = logging.getLogger(__name__)


@dataclass
class _DBExportSource:
    export_rows: Optional[List[Dict[str, Any]]]
    messages: Optional[List[MessageData]]
    source_items: List[Any]


@dataclass
class _DBExportPlan:
    target_author: str
    output_path: str
    ext: str
    fingerprint: Dict[str, Any]

class DBExportService:
    """
    Service responsible for exporting cached messages from the database into files.
    """
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def _manifest_dir(self, output_dir: str) -> str:
        return os.path.join(output_dir, ".export_state")

    def _manifest_path(self, output_dir: str, user_id: int) -> str:
        return os.path.join(self._manifest_dir(output_dir), f"{user_id}.json")

    def _build_export_fingerprint(
        self,
        user_id: int,
        messages: List[MessageData],
        *,
        as_json: bool,
        include_date: bool,
        json_profile: str,
    ) -> Dict[str, Any]:
        first = messages[0]
        last = messages[-1]
        return {
            "user_id": user_id,
            "message_count": len(messages),
            "first_message_id": first.message_id,
            "last_message_id": last.message_id,
            "first_timestamp": int(first.timestamp.timestamp()),
            "last_timestamp": int(last.timestamp.timestamp()),
            "as_json": as_json,
            "include_date": include_date,
            "json_profile": json_profile,
        }

    def _load_export_manifest(self, output_dir: str, user_id: int) -> Optional[Dict[str, Any]]:
        path = self._manifest_path(output_dir, user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return loaded if isinstance(loaded, dict) else None
        except Exception:
            return None

    def _persist_export_manifest(
        self,
        output_dir: str,
        user_id: int,
        payload: Dict[str, Any],
    ) -> None:
        os.makedirs(self._manifest_dir(output_dir), exist_ok=True)
        with open(self._manifest_path(output_dir, user_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    def _expected_export_paths(self, output_path: str, part_count: int) -> List[str]:
        if part_count <= 1:
            return [output_path]
        root, ext = os.path.splitext(output_path)
        paths = [output_path]
        for part in range(2, part_count + 1):
            paths.append(f"{root}_part{part}{ext}")
        return paths

    def _can_skip_export(
        self,
        output_dir: str,
        user_id: int,
        fingerprint: Dict[str, Any],
    ) -> Optional[str]:
        manifest = self._load_export_manifest(output_dir, user_id)
        if not manifest:
            return None
        if manifest.get("fingerprint") != fingerprint:
            return None

        output_path = manifest.get("output_path")
        if not output_path or not isinstance(output_path, str):
            return None

        part_count = manifest.get("part_count", 1)
        try:
            part_count = max(1, int(part_count))
        except Exception:
            return None

        expected_paths = self._expected_export_paths(output_path, part_count)
        if all(os.path.exists(path) for path in expected_paths):
            return output_path
        return None

    def _resolve_export_author_name(self, user_id: int, messages: List[MessageData]) -> str:
        db_user = self.storage.get_user(user_id)
        if db_user:
            formatted = UI.format_name(db_user)
            if formatted and formatted != "Unknown" and not formatted.startswith("ID:"):
                return formatted

        for m in messages:
            if m.user_id == user_id and m.author_name and m.author_name.strip():
                return m.author_name.strip()

        return f"User_{user_id}"

    def _resolve_export_author_name_from_rows(self, user_id: int, rows: List[Dict[str, Any]]) -> str:
        db_user = self.storage.get_user(user_id)
        if db_user:
            formatted = UI.format_name(db_user)
            if formatted and formatted != "Unknown" and not formatted.startswith("ID:"):
                return formatted

        for row in rows:
            if row.get("user_id") == user_id and row.get("author_name"):
                return str(row["author_name"]).strip()

        return f"User_{user_id}"

    def format_message(self, m: MessageData, as_json: bool = False, json_profile: str = "ai") -> str:
        """Formats a MessageData object into a string for file output."""
        if as_json:
            payload = self._serialize_json_message(m, profile=json_profile)
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        
        # Human-readable text format
        dt_str = m.timestamp.strftime("%Y-%m-%d][%H:%M:%S")
        reply_str = f" (в ответ на {m.reply_to_id})" if m.reply_to_id else ""
        fwd_str = f" [FWD from {m.fwd_from_id}]" if m.fwd_from_id else ""
        media_str = f" [{m.media_type}]" if m.media_type else ""
        
        # We use a placeholder for user_name if we have it in MessageData (I added it recently)
        author = m.author_name or f"User_{m.user_id}"
        header = f"[{dt_str}] <{author} ({m.user_id})>{reply_str}{fwd_str}{media_str}:"
        
        return f"{header}\n{m.text or '(пусто)'}"

    def _serialize_json_message(self, m: MessageData, profile: str = "ai") -> Dict[str, Any]:
        if profile == "full":
            return m.to_dict()
        if profile != "ai":
            raise ValueError(f"Unsupported JSON profile: {profile}")
        return self._serialize_ai_message(m)

    def _serialize_ai_message(self, m: MessageData) -> Dict[str, Any]:
        raw = m.raw_payload if isinstance(m.raw_payload, dict) else {}
        return self._serialize_ai_payload(
            message_id=m.message_id,
            chat_id=m.chat_id,
            user_id=m.user_id,
            author_name=m.author_name,
            timestamp=int(m.timestamp.timestamp()),
            text=m.text,
            reply_to_id=m.reply_to_id,
            media_type=m.media_type,
            fwd_from_id=m.fwd_from_id,
            context_group_id=m.context_group_id,
            is_service=m.is_service,
            raw=raw,
        )

    def _serialize_ai_row(self, row: Dict[str, Any]) -> str:
        raw_payload = row.get("raw_payload")
        if isinstance(raw_payload, str):
            try:
                raw = json.loads(raw_payload)
            except Exception:
                raw = {}
        elif isinstance(raw_payload, dict):
            raw = raw_payload
        else:
            raw = {}

        payload = self._serialize_ai_payload(
            message_id=row["message_id"],
            chat_id=row["chat_id"],
            user_id=row["user_id"],
            author_name=row.get("author_name"),
            timestamp=row["timestamp"],
            text=row.get("text"),
            reply_to_id=row.get("reply_to_id"),
            media_type=row.get("media_type"),
            fwd_from_id=row.get("fwd_from_id"),
            context_group_id=row.get("context_group_id"),
            is_service=bool(row.get("is_service")),
            raw=raw,
        )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _serialize_ai_payload(
        self,
        *,
        message_id: int,
        chat_id: int,
        user_id: int,
        author_name: Optional[str],
        timestamp: int,
        text: Optional[str],
        reply_to_id: Optional[int],
        media_type: Optional[str],
        fwd_from_id: Optional[int],
        context_group_id: Optional[str],
        is_service: bool,
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:
        reply_to = raw.get("reply_to") if isinstance(raw.get("reply_to"), dict) else {}
        reply_to_id = reply_to_id or reply_to.get("reply_to_msg_id")
        reply_to_top_id = reply_to.get("reply_to_top_id")
        forum_topic = True if reply_to.get("forum_topic") else None

        payload = {
            "edit_date": raw.get("edit_date"),
            "message_id": message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "author_name": author_name,
            "timestamp": timestamp,
            "text": text,
            "reply_to_id": reply_to_id,
            "reply_to_top_id": reply_to_top_id,
            "forum_topic": forum_topic,
            "media_type": media_type,
            "fwd_from_id": fwd_from_id,
            "context_group_id": context_group_id,
            "is_service": True if is_service else None,
            "reactions": self._extract_reaction_summary(raw),
        }
        return {k: v for k, v in payload.items() if v not in (None, "", [])}

    def _extract_reaction_summary(self, raw: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        reactions = raw.get("reactions")
        if not isinstance(reactions, dict):
            return None

        summary: List[Dict[str, Any]] = []
        for item in reactions.get("results") or []:
            if not isinstance(item, dict):
                continue
            reaction = item.get("reaction")
            count = item.get("count")
            emoji = self._reaction_label(reaction)
            if emoji is None or count is None:
                continue
            summary.append({"emoji": emoji, "count": count})

        return summary or None

    def _reaction_label(self, reaction: Any) -> Optional[str]:
        if not isinstance(reaction, dict):
            return None
        emoticon = reaction.get("emoticon")
        if emoticon:
            return emoticon
        if reaction.get("_") == "ReactionCustomEmoji":
            document_id = reaction.get("document_id")
            return f"custom:{document_id}" if document_id is not None else "custom"
        return reaction.get("_")

    def _write_batch_size(self, *, as_json: bool, json_profile: str) -> int:
        if not as_json:
            return 100
        if json_profile == "full":
            return 500
        return 1000

    def _load_export_source(
        self,
        *,
        user_id: int,
        as_json: bool,
        json_profile: str,
    ) -> Optional[_DBExportSource]:
        export_rows = None
        if as_json and json_profile == "ai":
            getter = getattr(self.storage, "get_user_export_rows", None)
            if callable(getter):
                export_rows = getter(user_id)

        messages = None if export_rows is not None else self.storage.get_user_messages(user_id)
        source_items = export_rows if export_rows is not None else messages
        if not source_items:
            return None

        return _DBExportSource(
            export_rows=export_rows,
            messages=messages,
            source_items=source_items,
        )

    def _prepare_export_plan(
        self,
        *,
        user_id: int,
        output_dir: str,
        source: _DBExportSource,
        as_json: bool,
        include_date: bool,
        json_profile: str,
    ) -> _DBExportPlan:
        if source.export_rows is not None:
            target_author = self._resolve_export_author_name_from_rows(user_id, source.export_rows)
            fingerprint = {
                "user_id": user_id,
                "message_count": len(source.export_rows),
                "first_message_id": source.export_rows[0]["message_id"],
                "last_message_id": source.export_rows[-1]["message_id"],
                "first_timestamp": source.export_rows[0]["timestamp"],
                "last_timestamp": source.export_rows[-1]["timestamp"],
                "as_json": as_json,
                "include_date": include_date,
                "json_profile": json_profile,
            }
        else:
            messages = source.messages or []
            messages.sort(key=lambda x: (x.timestamp, x.message_id))
            target_author = self._resolve_export_author_name(user_id, messages)
            fingerprint = self._build_export_fingerprint(
                user_id,
                messages,
                as_json=as_json,
                include_date=include_date,
                json_profile=json_profile,
            )

        safe_name = re.sub(r"[^\w\s-]", "", target_author).strip()
        safe_name = re.sub(r"[-\s]+", "_", safe_name)
        date_suffix = f"_date({datetime.now().strftime('%m-%d')})" if include_date else ""
        ext = ".jsonl" if as_json else ".txt"
        filename = f"{safe_name}_{user_id}{date_suffix}{ext}"

        return _DBExportPlan(
            target_author=target_author,
            output_path=os.path.join(output_dir, filename),
            ext=ext,
            fingerprint=fingerprint,
        )

    def _maybe_skip_unchanged_export(
        self,
        *,
        output_dir: str,
        user_id: int,
        fingerprint: Dict[str, Any],
        source_count: int,
    ) -> Optional[str]:
        unchanged_path = self._can_skip_export(output_dir, user_id, fingerprint)
        if not unchanged_path:
            return None

        telemetry.track_counter("db_export.skipped_unchanged", 1)
        logger.info(
            "DB export skipped as unchanged",
            extra={
                "event": "db_export_skipped",
                "metrics": {
                    "user_id": user_id,
                    "messages": source_count,
                    "path": unchanged_path,
                },
            },
        )
        return unchanged_path

    def _cleanup_existing_export_files(
        self,
        *,
        output_dir: str,
        user_id: int,
        ext: str,
        output_path: str,
    ) -> None:
        cleanup_patterns = [
            os.path.join(output_dir, f"*_{user_id}{ext}"),
            os.path.join(output_dir, f"*_{user_id}_part*{ext}"),
        ]
        for pattern in cleanup_patterns:
            for old_file in glob.glob(pattern):
                if os.path.abspath(old_file) == os.path.abspath(output_path):
                    continue
                try:
                    os.remove(old_file)
                    logger.debug(f"Removed old export file to prevent duplication: {old_file}")
                except Exception as e:
                    logger.warning(f"Could not remove old export file {old_file}: {e}")

    def _format_txt_export_block(
        self,
        *,
        message: MessageData,
        msg_lookup: Dict[int, MessageData],
        last_date: Any,
        last_author_id: Optional[int],
    ) -> tuple[str, Any, Optional[int]]:
        current_date = message.timestamp.date()
        formatted_block = ""

        if current_date != last_date:
            date_header = current_date.strftime("%d %B %Y")
            formatted_block += f"\n\n{'=' * 20} {date_header} {'=' * 20}\n\n"
            last_date = current_date
            last_author_id = None

        reply_context = ""
        if message.reply_to_id and message.reply_to_id in msg_lookup:
            target = msg_lookup[message.reply_to_id]
            clean_text = (target.text or "").replace("\n", " ").strip()
            snippet = (clean_text[:40] + "...") if len(clean_text) > 40 else clean_text
            if snippet:
                reply_context = f"        re: \"{snippet}\"\n"

        author = message.author_name or f"User_{message.user_id}"
        time_str = message.timestamp.strftime("%H:%M:%S")

        if message.user_id == last_author_id and not reply_context:
            formatted_block += f"        {message.text or '(пусто)'}\n"
            return formatted_block, last_date, last_author_id

        if message.user_id == last_author_id:
            formatted_block += "\n"

        header = f"[{time_str}] <{author} ({message.user_id})>:"
        formatted_block += f"{header}\n{reply_context}        {message.text or '(пусто)'}\n\n"
        return formatted_block, last_date, message.user_id

    async def _write_export_payloads(
        self,
        *,
        source: _DBExportSource,
        output_path: str,
        as_json: bool,
        json_profile: str,
    ) -> tuple[FileRotateWriter, int]:
        writer = FileRotateWriter(
            output_path,
            as_json=as_json,
            overwrite=True,
            persist_every_writes=25 if as_json else 5,
        )
        write_batch_size = self._write_batch_size(as_json=as_json, json_profile=json_profile)
        msg_lookup = {
            message.message_id: message
            for message in (source.messages or [])
        } if not as_json else {}

        last_date = None
        last_author_id = None
        pending_blocks: List[str] = []
        pending_count = 0

        async def flush_pending() -> None:
            nonlocal pending_blocks, pending_count
            if not pending_blocks:
                return
            await writer.write_block("".join(pending_blocks), pending_count)
            pending_blocks = []
            pending_count = 0

        count = 0
        iterable = source.export_rows if source.export_rows is not None else (source.messages or [])
        for item in iterable:
            if as_json:
                if source.export_rows is not None:
                    block = self._serialize_ai_row(item)
                else:
                    block = self.format_message(item, as_json=True, json_profile=json_profile)
            else:
                block, last_date, last_author_id = self._format_txt_export_block(
                    message=item,
                    msg_lookup=msg_lookup,
                    last_date=last_date,
                    last_author_id=last_author_id,
                )

            pending_blocks.append(block + "\n" if as_json else block)
            pending_count += 1

            if pending_count >= write_batch_size:
                await flush_pending()

            count += 1
            if count % 100 == 0:
                logger.debug(f"Exported {count}/{len(iterable)} messages from DB...")

        await flush_pending()
        await writer.finalize()
        return writer, count

    async def export_user_messages(
        self,
        user_id: int,
        output_dir: str = "DB_EXPORTS",
        as_json: bool = False,
        include_date: bool = False,
        json_profile: str = "ai",
    ) -> str:
        """
        Fetches all messages for a user from storage and writes them to parts using FileRotateWriter.
        Returns the base output path.
        """
        started_at = perf_counter()
        source = self._load_export_source(
            user_id=user_id,
            as_json=as_json,
            json_profile=json_profile,
        )
        if source is None:
            logger.warning(f"No messages found in DB for user {user_id}")
            return ""

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        plan = self._prepare_export_plan(
            user_id=user_id,
            output_dir=output_dir,
            source=source,
            as_json=as_json,
            include_date=include_date,
            json_profile=json_profile,
        )
        unchanged_path = self._maybe_skip_unchanged_export(
            output_dir=output_dir,
            user_id=user_id,
            fingerprint=plan.fingerprint,
            source_count=len(source.source_items),
        )
        if unchanged_path:
            return unchanged_path

        self._cleanup_existing_export_files(
            output_dir=output_dir,
            user_id=user_id,
            ext=plan.ext,
            output_path=plan.output_path,
        )
        writer, count = await self._write_export_payloads(
            source=source,
            output_path=plan.output_path,
            as_json=as_json,
            json_profile=json_profile,
        )
        elapsed_seconds = perf_counter() - started_at
        telemetry.track_counter("db_export.users", 1)
        telemetry.track_counter("db_export.messages", count)
        telemetry.track_duration("db_export.total", elapsed_seconds)
        logger.info(
            "DB export complete",
            extra={
                "event": "db_export_complete",
                "metrics": {
                    "user_id": user_id,
                    "messages": count,
                    "json": as_json,
                    "path": plan.output_path,
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "writer_write_calls": writer.write_calls,
                    "writer_bytes_written": writer.bytes_written,
                    "writer_rotations": writer.rotation_count,
                    "writer_state_persists": writer.state_persist_count,
                },
            },
        )
        self._persist_export_manifest(
            output_dir,
            user_id,
            {
                "output_path": plan.output_path,
                "part_count": writer.current_part,
                "fingerprint": plan.fingerprint,
            },
        )
        logger.info(f"DB Export complete for {plan.target_author}: {count} messages.")
        return plan.output_path
