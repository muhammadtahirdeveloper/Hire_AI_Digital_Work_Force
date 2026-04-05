"""Comprehensive tests for the AI Router (config/ai_router.py).

Tests cover:
- Tier enforcement (all tiers use Claude)
- API key resolution (env var)
- Model selection per tier
- Provider dispatch (mocked)
- Error handling
- Health check (mocked)
- Default config when user_agents row missing
"""

import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Mock config.database before importing AIRouter so we don't need psycopg2
# ---------------------------------------------------------------------------
import sys
import types

_mock_db_module = types.ModuleType("config.database")
_mock_db_module.SessionLocal = MagicMock
sys.modules.setdefault("config.database", _mock_db_module)

from config.ai_router import AIRouter  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine in a sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ============================================================================
# Tier Enforcement Tests
# ============================================================================


class TestTierEnforcement:
    """Test _enforce_tier — all tiers use Claude."""

    def setup_method(self):
        self.router = AIRouter()

    def test_trial_user_gets_claude(self):
        assert self.router._enforce_tier("claude", "trial") == "claude"

    def test_tier1_user_gets_claude(self):
        assert self.router._enforce_tier("claude", "tier1") == "claude"

    def test_tier2_user_gets_claude(self):
        assert self.router._enforce_tier("claude", "tier2") == "claude"

    def test_tier3_user_gets_claude(self):
        assert self.router._enforce_tier("claude", "tier3") == "claude"


# ============================================================================
# API Key Resolution Tests
# ============================================================================


class TestResolveKey:
    """Test _resolve_key — resolves Anthropic API key from env."""

    def setup_method(self):
        self.router = AIRouter()

    def test_env_fallback_claude(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-env"}):
            assert self.router._resolve_key("claude", None) == "ant-env"

    def test_missing_key_raises_value_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="No API key"):
                self.router._resolve_key("claude", None)


# ============================================================================
# Model Selection Tests
# ============================================================================


class TestModelSelection:
    """Test _get_model — correct model per tier."""

    def setup_method(self):
        self.router = AIRouter()

    def test_claude_trial(self):
        assert self.router._get_model("claude", "trial") == "claude-3-5-haiku-latest"

    def test_claude_tier1(self):
        assert self.router._get_model("claude", "tier1") == "claude-3-5-haiku-latest"

    def test_claude_tier2(self):
        assert self.router._get_model("claude", "tier2") == "claude-3-5-haiku-latest"

    def test_claude_tier3(self):
        assert self.router._get_model("claude", "tier3") == "claude-sonnet-4-5-20250514"

    def test_unknown_tier_returns_default(self):
        assert self.router._get_model("claude", "unknown_tier") == "claude-3-5-haiku-latest"


# ============================================================================
# User Config Tests
# ============================================================================


class TestGetUserConfig:
    """Test _get_user_config — reads from DB or returns defaults."""

    def setup_method(self):
        self.router = AIRouter()

    def test_default_when_no_db_row(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None

        with patch("config.ai_router.SessionLocal", return_value=mock_session):
            provider, key, tier = self.router._get_user_config("user-123")

        assert provider == "claude"
        assert key is None
        assert tier == "trial"

    def test_reads_db_row(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (
            "claude", None, "tier2"
        )

        with patch("config.ai_router.SessionLocal", return_value=mock_session):
            provider, key, tier = self.router._get_user_config("user-456")

        assert provider == "claude"
        assert tier == "tier2"

    def test_null_provider_defaults_to_claude(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (None, None, None)

        with patch("config.ai_router.SessionLocal", return_value=mock_session):
            provider, key, tier = self.router._get_user_config("user-789")

        assert provider == "claude"
        assert tier == "trial"

    def test_db_exception_returns_defaults(self):
        with patch("config.ai_router.SessionLocal", side_effect=Exception("DB down")):
            provider, key, tier = self.router._get_user_config("user-err")

        assert provider == "claude"
        assert key is None
        assert tier == "trial"


# ============================================================================
# Generate Tests (mocked providers)
# ============================================================================


class TestGenerate:
    """Test generate() — dispatches to Claude with mocks."""

    def setup_method(self):
        self.router = AIRouter()

    def test_generate_calls_claude_for_trial_user(self):
        mock_result = {"content": "Hello!", "provider": "claude", "model": "claude-3-5-haiku-latest"}

        with patch.object(self.router, "_get_user_config", return_value=("claude", None, "trial")), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u1", "system", "hello"))

        assert result["provider"] == "claude"
        assert result["content"] == "Hello!"

    def test_generate_calls_claude_for_tier2_user(self):
        mock_result = {"content": "Hi!", "provider": "claude", "model": "claude-3-5-haiku-latest"}

        with patch.object(self.router, "_get_user_config", return_value=("claude", None, "tier2")), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u2", "system", "hello"))

        assert result["provider"] == "claude"

    def test_generate_calls_claude_for_tier3_user(self):
        mock_result = {"content": "Claude!", "provider": "claude", "model": "claude-sonnet-4-5-20250514"}

        with patch.object(self.router, "_get_user_config", return_value=("claude", None, "tier3")), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u5", "system", "hello"))

        assert result["provider"] == "claude"

    def test_claude_failure_returns_error(self):
        with patch.object(self.router, "_get_user_config", return_value=("claude", None, "trial")), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, side_effect=Exception("Claude down")):

            result = _run(self.router.generate("u4", "system", "hello"))

        assert result["provider"] == "none"
        assert result["model"] == "none"
        assert "error" in result
        assert "unable to process" in result["content"].lower()


# ============================================================================
# Health Check Tests
# ============================================================================


class TestCheckProvider:
    """Test check_provider() — health check for Claude."""

    def setup_method(self):
        self.router = AIRouter()

    def test_healthy_provider(self):
        mock_result = {"content": "Hello", "provider": "claude", "model": "claude-3-5-haiku-latest"}

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.check_provider("claude"))

        assert result["status"] == "healthy"
        assert result["provider"] == "claude"
        assert result["model"] == "claude-3-5-haiku-latest"

    def test_unhealthy_provider(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "key"}), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, side_effect=Exception("timeout")):

            result = _run(self.router.check_provider("claude"))

        assert result["status"] == "error"
        assert result["provider"] == "claude"
        assert "timeout" in result["error"]

    def test_missing_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = _run(self.router.check_provider("claude"))

        assert result["status"] == "error"
        assert "No API key" in result["error"]


# ============================================================================
# Provider Map Tests
# ============================================================================


class TestProviderMap:
    """Test that all provider methods exist and map correctly."""

    def setup_method(self):
        self.router = AIRouter()

    def test_all_providers_have_methods(self):
        for provider, method_name in self.router.PROVIDER_MAP.items():
            assert hasattr(self.router, method_name), (
                f"Missing method {method_name} for provider {provider}"
            )

    def test_all_providers_have_models(self):
        for provider in self.router.PROVIDER_MAP:
            assert provider in self.router.PROVIDER_MODELS, (
                f"Missing model config for provider {provider}"
            )

    def test_all_providers_have_env_map(self):
        for provider in self.router.PROVIDER_MAP:
            assert provider in self.router._ENV_MAP, (
                f"Missing env var mapping for provider {provider}"
            )

    def test_managed_providers_are_subset_of_all(self):
        assert self.router.MANAGED_PROVIDERS.issubset(set(self.router.PROVIDER_MAP.keys()))

    def test_one_provider_registered(self):
        assert len(self.router.PROVIDER_MAP) == 1
        assert set(self.router.PROVIDER_MAP.keys()) == {"claude"}
