"""Tests for the cron preflight and health-check freshness logic."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.health import compute_freshness
from runner.model_adapters import required_env_vars
from runner.cron_evaluate import preflight


class TestRequiredEnvVars:
    def test_maps_provider_keys(self):
        out = required_env_vars(["gpt-5.1", "claude-opus-4-8", "gemini-2.5-pro"])
        assert out == {
            "OPENAI_API_KEY": ["gpt-5.1"],
            "ANTHROPIC_API_KEY": ["claude-opus-4-8"],
            "GOOGLE_API_KEY": ["gemini-2.5-pro"],
        }

    def test_groups_multiple_models_per_var(self):
        out = required_env_vars(["gpt-5.1", "gpt-4.1-mini"])
        assert out == {"OPENAI_API_KEY": ["gpt-5.1", "gpt-4.1-mini"]}

    def test_unmappable_model_flagged(self):
        out = required_env_vars(["totally-made-up-model"])
        assert out == {"<no provider mapping>": ["totally-made-up-model"]}

    def test_local_needs_no_key(self):
        assert required_env_vars(["local/llama3"]) == {}


class TestPreflight:
    def test_missing_database_url_is_fatal(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        problems = preflight(["gpt-5.1"], allow_sqlite=False)
        assert any("DATABASE_URL" in p for p in problems)

    def test_allow_sqlite_waives_database_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        assert preflight(["gpt-5.1"], allow_sqlite=True) == []

    def test_missing_api_key_is_fatal(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgres://x")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        problems = preflight(["claude-opus-4-8"], allow_sqlite=False)
        assert any("ANTHROPIC_API_KEY" in p for p in problems)

    def test_all_present_passes(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgres://x")
        monkeypatch.setenv("OPENAI_API_KEY", "x")
        assert preflight(["gpt-5.1"], allow_sqlite=False) == []


class TestComputeFreshness:
    NOW = datetime(2026, 6, 8, 6, 0, tzinfo=timezone.utc)

    def test_no_runs(self):
        out = compute_freshness(None, self.NOW, 36.0)
        assert out == {"last_run": None, "fresh": False, "reason": "no_runs"}

    def test_recent_run_is_fresh(self):
        last = (self.NOW - timedelta(hours=3)).isoformat()
        out = compute_freshness(last, self.NOW, 36.0)
        assert out["fresh"] is True
        assert out["last_run_age_hours"] == 3.0

    def test_old_run_is_stale(self):
        last = (self.NOW - timedelta(hours=50)).isoformat()
        out = compute_freshness(last, self.NOW, 36.0)
        assert out["fresh"] is False
        assert out["reason"] == "stale"

    def test_boundary_is_fresh(self):
        last = (self.NOW - timedelta(hours=36)).isoformat()
        assert compute_freshness(last, self.NOW, 36.0)["fresh"] is True

    def test_naive_timestamp_assumed_utc(self):
        last = (self.NOW - timedelta(hours=2)).replace(tzinfo=None).isoformat()
        assert compute_freshness(last, self.NOW, 36.0)["fresh"] is True

    def test_unparseable_timestamp(self):
        out = compute_freshness("not-a-date", self.NOW, 36.0)
        assert out["fresh"] is False
        assert out["reason"] == "unparseable_timestamp"
