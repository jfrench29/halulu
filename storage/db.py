"""Database storage layer.

Production: PostgreSQL via DATABASE_URL (connection-pooled, thread-safe).
Local dev:  SQLite fallback when DATABASE_URL is not set.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = Path(__file__).parent / "results.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResultsDB:
    """Thread-safe DB interface supporting both PostgreSQL and SQLite.

    PostgreSQL uses a ThreadedConnectionPool for concurrent access.
    SQLite uses per-thread connections via threading.local().
    """

    def __init__(self, db_url: str | None = None):
        self._url = db_url or os.environ.get("DATABASE_URL")
        self._is_postgres = bool(self._url)
        self._placeholder = "%s" if self._is_postgres else "?"

        if self._is_postgres:
            import psycopg2.pool

            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=self._url,
                connect_timeout=5,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
        else:
            self._local = threading.local()

        self._init_tables()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        """Get a per-thread SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(DEFAULT_SQLITE_PATH))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _conn(self):
        """Yield a connection. For PostgreSQL, acquires from pool and returns it."""
        if self._is_postgres:
            conn = self._pool.getconn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._pool.putconn(conn)
        else:
            conn = self._get_sqlite_conn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_tables(self):
        if self._is_postgres:
            serial = "SERIAL PRIMARY KEY"
        else:
            serial = "INTEGER PRIMARY KEY AUTOINCREMENT"

        stmts = [
            f"""CREATE TABLE IF NOT EXISTS eval_runs (
                id {serial},
                run_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                dataset TEXT NOT NULL,
                models TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS eval_results (
                id {serial},
                run_id TEXT NOT NULL,
                model TEXT NOT NULL,
                test_id INTEGER NOT NULL,
                category TEXT,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                grade TEXT NOT NULL,
                hallucination_subtype TEXT,
                confidence REAL,
                explanation TEXT,
                latency_ms REAL,
                timestamp TEXT NOT NULL
            )""",
            f"""CREATE TABLE IF NOT EXISTS hall_of_fame (
                id {serial},
                model TEXT NOT NULL,
                test_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                hallucination_subtype TEXT,
                added_at TEXT NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS idx_results_run ON eval_results(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_results_model ON eval_results(model)",
            "CREATE INDEX IF NOT EXISTS idx_results_grade ON eval_results(grade)",
            "CREATE INDEX IF NOT EXISTS idx_results_ts ON eval_results(timestamp)",
        ]

        with self._conn() as conn:
            cur = conn.cursor()
            for stmt in stmts:
                cur.execute(stmt)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ph(self, n: int = 1) -> str:
        return ", ".join([self._placeholder] * n)

    def _fetchall_dicts(self, cursor) -> list[dict]:
        if self._is_postgres:
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        else:
            return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save_run(self, run_id: str, dataset: str, models: list[str]):
        with self._conn() as conn:
            conn.cursor().execute(
                f"INSERT INTO eval_runs (run_id, timestamp, dataset, models) VALUES ({self._ph(4)})",
                (run_id, _utcnow(), dataset, json.dumps(models)),
            )

    def save_results_batch(self, results: list[dict]):
        """Batch insert evaluation results in a single transaction."""
        if not results:
            return
        with self._conn() as conn:
            cur = conn.cursor()
            for r in results:
                cur.execute(
                    f"""INSERT INTO eval_results
                    (run_id, model, test_id, category, prompt, response, grade,
                     hallucination_subtype, confidence, explanation, latency_ms, timestamp)
                    VALUES ({self._ph(12)})""",
                    (
                        r["run_id"], r["model"], r["test_id"], r["category"],
                        r["prompt"], r["response"], r["grade"],
                        r.get("hallucination_subtype"), r.get("confidence", 1.0),
                        r.get("explanation", ""), r.get("latency_ms", 0), _utcnow(),
                    ),
                )

    def save_result(self, **kwargs):
        """Insert a single result. Prefer save_results_batch for bulk inserts."""
        self.save_results_batch([kwargs])

    def add_to_hall_of_fame(
        self,
        model: str,
        test_id: int,
        prompt: str,
        response: str,
        hallucination_subtype: str | None,
    ):
        with self._conn() as conn:
            conn.cursor().execute(
                f"""INSERT INTO hall_of_fame
                (model, test_id, prompt, response, hallucination_subtype, added_at)
                VALUES ({self._ph(6)})""",
                (model, test_id, prompt, response, hallucination_subtype, _utcnow()),
            )

    # ------------------------------------------------------------------
    # Reads — all bounded with LIMIT
    # ------------------------------------------------------------------

    def get_results_for_run(self, run_id: str, limit: int = 5000) -> list[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM eval_results WHERE run_id = {self._placeholder} LIMIT {limit}",
                (run_id,),
            )
            return self._fetchall_dicts(cur)

    def get_results_for_model(self, model: str, limit: int = 5000) -> list[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM eval_results WHERE model = {self._placeholder} ORDER BY timestamp DESC LIMIT {limit}",
                (model,),
            )
            return self._fetchall_dicts(cur)

    def get_all_runs(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM eval_runs ORDER BY timestamp DESC LIMIT {limit}")
            return self._fetchall_dicts(cur)

    def get_hall_of_fame(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM hall_of_fame ORDER BY added_at DESC LIMIT {limit}")
            return self._fetchall_dicts(cur)

    def get_model_names(self) -> list[str]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT model FROM eval_results ORDER BY model")
            if self._is_postgres:
                return [row[0] for row in cur.fetchall()]
            else:
                return [row["model"] for row in cur.fetchall()]

    def get_latest_results_per_model(self) -> dict[str, list[dict]]:
        """Get the most recent run's results for each model — single query."""
        with self._conn() as conn:
            cur = conn.cursor()

            if self._is_postgres:
                # Use window function (Postgres)
                cur.execute("""
                    SELECT * FROM (
                        SELECT er.*,
                               ROW_NUMBER() OVER (
                                   PARTITION BY er.model
                                   ORDER BY er.timestamp DESC
                               ) AS _latest_run_rank
                        FROM eval_results er
                        INNER JOIN (
                            SELECT model, MAX(run_id) AS latest_run
                            FROM eval_results
                            GROUP BY model
                        ) lr ON er.model = lr.model AND er.run_id = lr.latest_run
                    ) ranked WHERE _latest_run_rank <= 500
                """)
            else:
                # SQLite-compatible: subquery approach
                cur.execute("""
                    SELECT er.* FROM eval_results er
                    INNER JOIN (
                        SELECT model, run_id FROM eval_results
                        GROUP BY model
                        HAVING timestamp = MAX(timestamp)
                    ) latest ON er.model = latest.model AND er.run_id = latest.run_id
                """)

            rows = self._fetchall_dicts(cur)

            # Remove internal ranking column if present
            out: dict[str, list[dict]] = {}
            for row in rows:
                row.pop("_latest_run_rank", None)
                out.setdefault(row["model"], []).append(row)
            return out

    def get_trend_data(self, models: list[str] | None = None, days: int = 90) -> list[dict]:
        """Server-side aggregation for trend charts. Returns per-model, per-date stats."""
        with self._conn() as conn:
            cur = conn.cursor()

            date_func = "DATE(timestamp)" if self._is_postgres else "DATE(timestamp)"

            if models:
                placeholders = ", ".join([self._placeholder] * len(models))
                cur.execute(
                    f"""SELECT
                            {date_func} AS eval_date,
                            model,
                            COUNT(*) AS total,
                            SUM(CASE WHEN grade = 'correct' THEN 1 ELSE 0 END) AS correct,
                            SUM(CASE WHEN grade = 'hallucinated' THEN 1 ELSE 0 END) AS hallucinated,
                            SUM(CASE WHEN grade = 'refused' THEN 1 ELSE 0 END) AS refused
                        FROM eval_results
                        WHERE model IN ({placeholders})
                        GROUP BY {date_func}, model
                        ORDER BY eval_date DESC
                        LIMIT 1000""",
                    tuple(models),
                )
            else:
                cur.execute(
                    f"""SELECT
                            {date_func} AS eval_date,
                            model,
                            COUNT(*) AS total,
                            SUM(CASE WHEN grade = 'correct' THEN 1 ELSE 0 END) AS correct,
                            SUM(CASE WHEN grade = 'hallucinated' THEN 1 ELSE 0 END) AS hallucinated,
                            SUM(CASE WHEN grade = 'refused' THEN 1 ELSE 0 END) AS refused
                        FROM eval_results
                        GROUP BY {date_func}, model
                        ORDER BY eval_date DESC
                        LIMIT 1000"""
                )

            return self._fetchall_dicts(cur)

    def get_result_count(self) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM eval_results")
            row = cur.fetchone()
            return row[0] if isinstance(row, tuple) else row["COUNT(*)"]

    def close(self):
        if self._is_postgres:
            self._pool.closeall()
