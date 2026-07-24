"""Small local audit store. Replaceable with managed Postgres for multi-instance deployments."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS processing_audit (
                id TEXT PRIMARY KEY, form_slug TEXT NOT NULL, image_hashes TEXT NOT NULL,
                image_quality TEXT NOT NULL DEFAULT '[]', ocr_text TEXT, ai_result TEXT,
                validation_result TEXT, final_data TEXT, status TEXT NOT NULL,
                submission_id TEXT, error TEXT, retry_history TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")

    def _connect(self):
        return sqlite3.connect(self.path)

    def create(self, process_id: str, form: str, hashes: list[str], quality: list[dict], ocr_text: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("INSERT INTO processing_audit (id,form_slug,image_hashes,image_quality,ocr_text,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                       (process_id, form, json.dumps(hashes), json.dumps(quality), ocr_text, "extracted", now, now))

    def update(self, process_id: str, **values: Any) -> None:
        if not values:
            return
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        columns = ", ".join(f"{name}=?" for name in values)
        with self._connect() as db:
            db.execute(f"UPDATE processing_audit SET {columns} WHERE id=?", (*[json.dumps(v) if isinstance(v, (dict, list)) else v for v in values.values()], process_id))

    def duplicate_hashes(self, form: str, hashes: list[str]) -> list[str]:
        with self._connect() as db:
            rows = db.execute("SELECT id,image_hashes FROM processing_audit WHERE form_slug=? AND status IN ('extracted','review','submitted')", (form,)).fetchall()
        return [row[0] for row in rows if set(hashes) & set(json.loads(row[1]))]

    def get(self, process_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM processing_audit WHERE id=?", (process_id,)).fetchone()
            cols = [d[0] for d in db.execute("SELECT * FROM processing_audit LIMIT 1").description]
        return dict(zip(cols, row)) if row else None
