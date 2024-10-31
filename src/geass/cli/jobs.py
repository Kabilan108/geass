# Author: Tony K. Okeke
# Date:   03.17.2024

from typing import Optional
from pathlib import Path
import sqlite3
import json

from .models import Job


class JobLogger:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path).expanduser().resolve()
        self._create_table()

    def _create_table(self):
        if not self.db_path.exists():
            self.db_path.touch()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    file TEXT NOT NULL,
                    call_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transcript TEXT,
                    time_taken REAL
                )
                """
            )

    def save_job(self, job: Job) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (name, file, call_id, status)
                VALUES (?, ?, ?, ?)
                """,
                (job.name, str(job.file), job.call_id, job.status),
            )
            conn.commit()
            return cursor.lastrowid

    def update_job(self, job: Job):
        with sqlite3.connect(self.db_path) as conn:
            transcript = job.transcript.model_dump_json() if job.transcript else None
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, transcript = ?
                WHERE id = ?
            """,
                (job.status, transcript, job.id),
            )

    def get_jobs(self, status: str = None, limit: int = -1) -> list[Job]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM jobs"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY start_time DESC"

            if limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()

            job_data = []
            for r in rows:
                d = dict(r)
                d["transcript"] = (
                    json.loads(d["transcript"]) if d["transcript"] else None
                )
                job_data.append(Job(**d))

            return job_data

    def get_job(self, id: int) -> Optional[Job]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM jobs WHERE id = ?", (id,)).fetchone()
                if row:
                    d = dict(row)
                    d["transcript"] = (
                        json.loads(d["transcript"]) if d["transcript"] else None
                    )
                    return Job(**d)
                else:
                    raise ValueError(f"No job found with ID {id}")
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Database error: {e}")
        except Exception as e:
            raise ValueError(e)
