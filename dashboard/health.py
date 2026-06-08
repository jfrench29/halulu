"""Lightweight health check server.

Runs alongside Streamlit on a separate port. Railway and Cloudflare
can hit /health to verify the service is alive and the DB is reachable.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from storage.db import ResultsDB

logger = logging.getLogger(__name__)

# A daily cron should always have produced a run within this window. The
# default leaves a generous grace period (run duration + one missed day)
# before a missed briefing is flagged as stale. Override via env.
DEFAULT_FRESHNESS_MAX_HOURS = 36.0

# Singleton DB — reuses the connection pool across health checks.
_db: ResultsDB | None = None


def _get_db() -> ResultsDB:
    global _db
    if _db is None:
        _db = ResultsDB()
    return _db


def _max_freshness_hours() -> float:
    try:
        return float(os.environ.get("FRESHNESS_MAX_HOURS", DEFAULT_FRESHNESS_MAX_HOURS))
    except ValueError:
        return DEFAULT_FRESHNESS_MAX_HOURS


def compute_freshness(last_run_iso: str | None, now: datetime, max_hours: float) -> dict:
    """Build the freshness portion of the health payload.

    Pure function (no I/O) so it can be unit-tested. ``last_run_iso`` is the
    most recent run timestamp, or None if no runs exist yet.
    """
    if last_run_iso is None:
        return {"last_run": None, "fresh": False, "reason": "no_runs"}

    try:
        last_run = datetime.fromisoformat(last_run_iso)
    except ValueError:
        return {"last_run": last_run_iso, "fresh": False, "reason": "unparseable_timestamp"}

    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)

    age_hours = (now - last_run).total_seconds() / 3600.0
    out = {
        "last_run": last_run_iso,
        "last_run_age_hours": round(age_hours, 1),
        "fresh": age_hours <= max_hours,
    }
    if not out["fresh"]:
        out["reason"] = "stale"
    return out


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            try:
                db = _get_db()
                payload = {"status": "ok", "results": db.get_result_count()}
                # Freshness: surface a missed/stale briefing without failing the
                # check (a stale cron must not trip Railway into restarting the
                # web service — only an unreachable DB is "unhealthy").
                payload.update(
                    compute_freshness(
                        db.get_latest_run_timestamp(),
                        datetime.now(timezone.utc),
                        _max_freshness_hours(),
                    )
                )
                body = json.dumps(payload)
                self.send_response(200)
            except Exception as e:
                logger.exception("Health check failed")
                body = json.dumps({"status": "unhealthy", "error": "database_unreachable"})
                self.send_response(503)
        else:
            body = json.dumps({"status": "not_found"})
            self.send_response(404)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass  # Silence access logs


def main():
    port = int(os.environ.get("HEALTH_PORT", "8081"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health check listening on :{port}/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
