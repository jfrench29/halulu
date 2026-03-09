"""Lightweight health check server.

Runs alongside Streamlit on a separate port. Railway and Cloudflare
can hit /health to verify the service is alive and the DB is reachable.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            try:
                from storage.db import ResultsDB
                db = ResultsDB()
                count = db.get_result_count()
                db.close()
                body = json.dumps({"status": "ok", "results": count})
                self.send_response(200)
            except Exception as e:
                body = json.dumps({"status": "unhealthy", "error": str(e)})
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
