"""
Telegram as free cloud storage backend.

Uses a private Telegram channel/chat to store ILLIP snapshots, memory
exports, and file backups. Each snapshot is sent as a document with a
structured caption for discovery.

Requires env vars:
  TELEGRAM_STORAGE_TOKEN   — bot token (can reuse the chat bot's token)
  TELEGRAM_STORAGE_CHAT_ID — private channel/group ID (negative number for groups)

Install: python-telegram-bot is already in requirements.
"""

import io
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.utils import logger

_CAPTION_PREFIX = "ILLIP_SNAPSHOT"


def _token() -> str:
    return os.environ.get("TELEGRAM_STORAGE_TOKEN", "") or settings.telegram_bot_token


def _chat_id() -> str:
    return os.environ.get("TELEGRAM_STORAGE_CHAT_ID", "")


class TelegramStorage:
    def __init__(self):
        self._token = _token()
        self._chat_id = _chat_id()

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def _bot(self):
        from telegram import Bot
        return Bot(token=self._token)

    # ── upload ─────────────────────────────────────────────────────────────

    async def upload_snapshot(self, name: str, data: dict) -> Optional[str]:
        if not self.is_configured():
            logger.warning("TelegramStorage: not configured")
            return None
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        caption = f"{_CAPTION_PREFIX}:{name}:{ts}"
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode()
        try:
            bot = self._bot()
            doc = io.BytesIO(payload)
            doc.name = f"{name}_{ts}.json"
            msg = await bot.send_document(
                chat_id=self._chat_id,
                document=doc,
                caption=caption,
            )
            file_id = msg.document.file_id
            logger.info(f"TelegramStorage: uploaded snapshot '{name}' → {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"TelegramStorage upload_snapshot error: {e}")
            return None

    async def upload_file(self, path: str, caption: str = "") -> Optional[str]:
        if not self.is_configured():
            return None
        try:
            bot = self._bot()
            with open(path, "rb") as f:
                msg = await bot.send_document(
                    chat_id=self._chat_id,
                    document=f,
                    caption=caption or Path(path).name,
                )
            return msg.document.file_id
        except Exception as e:
            logger.error(f"TelegramStorage upload_file error: {e}")
            return None

    # ── list / download ────────────────────────────────────────────────────

    async def list_snapshots(self) -> list[dict]:
        """
        Fetches recent messages from storage chat and filters snapshots.
        Telegram Bot API doesn't support full history search — we use
        getUpdates or forwardMessages workaround. For simplicity, we maintain
        a local index at data/telegram_storage/index.jsonl and sync from it.
        """
        index_path = settings.get_data_path() / "telegram_storage" / "index.jsonl"
        if not index_path.exists():
            return []
        snapshots = []
        for line in index_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("caption", "").startswith(_CAPTION_PREFIX):
                    parts = entry["caption"].split(":")
                    snapshots.append({
                        "name": parts[1] if len(parts) > 1 else "unknown",
                        "timestamp": parts[2] if len(parts) > 2 else "",
                        "file_id": entry.get("file_id", ""),
                        "size": entry.get("size", 0),
                    })
            except Exception:
                continue
        return sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)

    def _write_index(self, file_id: str, caption: str, size: int = 0) -> None:
        index_dir = settings.get_data_path() / "telegram_storage"
        index_dir.mkdir(parents=True, exist_ok=True)
        entry = {"file_id": file_id, "caption": caption, "size": size,
                 "ts": datetime.now(timezone.utc).isoformat()}
        with open(index_dir / "index.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def download_snapshot(self, file_id: str) -> Optional[dict]:
        if not self.is_configured():
            return None
        try:
            bot = self._bot()
            tg_file = await bot.get_file(file_id)
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)
            data = json.loads(Path(tmp_path).read_text())
            Path(tmp_path).unlink(missing_ok=True)
            return data
        except Exception as e:
            logger.error(f"TelegramStorage download_snapshot error: {e}")
            return None

    # ── high-level backup / restore ────────────────────────────────────────

    async def backup_memory(self) -> bool:
        memory_dir = settings.get_memory_path()
        if not memory_dir.exists():
            logger.warning("TelegramStorage: memory dir not found")
            return False
        data: dict = {}
        for f in memory_dir.rglob("*.json"):
            try:
                data[str(f.relative_to(memory_dir))] = json.loads(f.read_text())
            except Exception:
                pass
        if not data:
            logger.info("TelegramStorage: no memory files to backup")
            return False
        file_id = await self.upload_snapshot("memory_backup", data)
        if file_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self._write_index(file_id, f"{_CAPTION_PREFIX}:memory_backup:{ts}", len(str(data)))
        return file_id is not None

    async def backup_knowledge_graph(self) -> bool:
        kg_dir = settings.get_data_path() / "knowledge_graph"
        if not kg_dir.exists():
            logger.warning("TelegramStorage: knowledge_graph dir not found")
            return False
        data: dict = {}
        for f in kg_dir.rglob("*.json"):
            try:
                data[str(f.relative_to(kg_dir))] = json.loads(f.read_text())
            except Exception:
                pass
        if not data:
            return False
        file_id = await self.upload_snapshot("kg_backup", data)
        if file_id:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self._write_index(file_id, f"{_CAPTION_PREFIX}:kg_backup:{ts}", len(str(data)))
        return file_id is not None

    async def restore_latest(self, name: str) -> Optional[dict]:
        snapshots = await self.list_snapshots()
        matches = [s for s in snapshots if s["name"] == name]
        if not matches:
            return None
        latest = matches[0]  # already sorted desc by timestamp
        return await self.download_snapshot(latest["file_id"])


_storage: Optional[TelegramStorage] = None


def get_telegram_storage() -> TelegramStorage:
    global _storage
    if _storage is None:
        _storage = TelegramStorage()
    return _storage
