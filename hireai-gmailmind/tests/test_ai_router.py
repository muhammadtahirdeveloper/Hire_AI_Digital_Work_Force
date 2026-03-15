"""Comprehensive tests for the AI Router (config/ai_router.py).

Tests cover:
- Tier enforcement (free vs paid)
- API key resolution (BYOK vs env)
- Model selection per provider + tier
- Provider dispatch (mocked)
- Fallback on provider failure
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
    """Test _enforce_tier — free users can only use free providers."""

    def setup_method(self):
        self.router = AIRouter()

    def test_trial_user_blocked_from_openai(self):
        assert self.router._enforce_tier("openai", "trial") == "gemini"

    def test_trial_user_blocked_from_claude(self):
        assert self.router._enforce_tier("claude", "trial") == "gemini"

    def test_tier1_user_blocked_from_openai(self):
        assert self.router._enforce_tier("openai", "tier1") == "gemini"

    def test_tier1_user_blocked_from_claude(self):
        assert self.router._enforce_tier("claude", "tier1") == "gemini"

    def test_tier2_user_allowed_openai(self):
        assert self.router._enforce_tier("openai", "tier2") == "openai"

    def test_tier2_user_allowed_claude(self):
        assert self.router._enforce_tier("claude", "tier2") == "claude"

    def test_tier3_user_allowed_openai(self):
        assert self.router._enforce_tier("openai", "tier3") == "openai"

    def test_tier3_user_allowed_claude(self):
        assert self.router._enforce_tier("claude", "tier3") == "claude"

    def test_trial_user_allowed_gemini(self):
        assert self.router._enforce_tier("gemini", "trial") == "gemini"

    def test_trial_user_allowed_groq(self):
        assert self.router._enforce_tier("groq", "trial") == "groq"

    def test_tier1_user_allowed_gemini(self):
        assert self.router._enforce_tier("gemini", "tier1") == "gemini"

    def test_tier1_user_allowed_groq(self):
        assert self.router._enforce_tier("groq", "tier1") == "groq"

    def test_tier2_user_allowed_gemini(self):
        assert self.router._enforce_tier("gemini", "tier2") == "gemini"

    def test_tier3_user_allowed_groq(self):
        assert self.router._enforce_tier("groq", "tier3") == "groq"


# ============================================================================
# API Key Resolution Tests
# ============================================================================


class TestResolveKey:
    """Test _resolve_key — BYOK preferred, then env var, else error."""

    def setup_method(self):
        self.router = AIRouter()

    def test_byok_preferred_over_env(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            assert self.router._resolve_key("gemini", "my-byok-key") == "my-byok-key"

    def test_env_fallback_when_no_byok(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            assert self.router._resolve_key("gemini", None) == "env-key"

    def test_env_fallback_groq(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-env"}):
            assert self.router._resolve_key("groq", None) == "groq-env"

    def test_env_fallback_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "oai-env"}):
            assert self.router._resolve_key("openai", None) == "oai-env"

    def test_env_fallback_claude(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-env"}):
            assert self.router._resolve_key("claude", None) == "ant-env"

    def test_missing_key_raises_value_error(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if it exists
            os.environ.pop("GEMINI_API_KEY", None)
            with pytest.raises(ValueError, match="No API key"):
                self.router._resolve_key("gemini", None)

    def test_empty_byok_uses_env(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            # Empty string is falsy, should fall back to env
            assert self.router._resolve_key("gemini", "") == "env-key"


# ============================================================================
# Model Selection Tests
# ============================================================================


class TestModelSelection:
    """Test _get_model — correct model per provider + tier."""

    def setup_method(self):
        self.router = AIRouter()

    # Gemini
    def test_gemini_trial(self):
        assert self.router._get_model("gemini", "trial") == "gemini-1.5-flash"

    def test_gemini_tier1(self):
        assert self.router._get_model("gemini", "tier1") == "gemini-1.5-flash"

    def test_gemini_tier2(self):
        assert self.router._get_model("gemini", "tier2") == "gemini-1.5-pro"

    def test_gemini_tier3(self):
        assert self.router._get_model("gemini", "tier3") == "gemini-1.5-pro"

    # Groq
    def test_groq_trial(self):
        assert self.router._get_model("groq", "trial") == "llama-3.1-8b-instant"

    def test_groq_tier2(self):
        assert self.router._get_model("groq", "tier2") == "llama-3.1-70b-versatile"

    # OpenAI
    def test_openai_tier1(self):
        assert self.router._get_model("openai", "tier1") == "gpt-4o-mini"

    def test_openai_tier2(self):
        assert self.router._get_model("openai", "tier2") == "gpt-4o"

    # Claude
    def test_claude_tier1(self):
        assert self.router._get_model("claude", "tier1") == "claude-haiku-3-5"

    def test_claude_tier3(self):
        assert self.router._get_model("claude", "tier3") == "claude-sonnet-4-5"

    # Unknown
    def test_unknown_provider_returns_default(self):
        assert self.router._get_model("unknown", "tier1") == "gemini-1.5-flash"

    def test_unknown_tier_returns_default(self):
        assert self.router._get_model("gemini", "unknown_tier") == "gemini-1.5-flash"


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

        assert provider == "gemini"
        assert key is None
        assert tier == "trial"

    def test_reads_db_row(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (
            "groq", "byok-key-123", "tier2"
        )

        with patch("config.ai_router.SessionLocal", return_value=mock_session):
            provider, key, tier = self.router._get_user_config("user-456")

        assert provider == "groq"
        assert key == "byok-key-123"
        assert tier == "tier2"

    def test_null_provider_defaults_to_gemini(self):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = (None, None, None)

        with patch("config.ai_router.SessionLocal", return_value=mock_session):
            provider, key, tier = self.router._get_user_config("user-789")

        assert provider == "gemini"
        assert tier == "trial"

    def test_db_exception_returns_defaults(self):
        with patch("config.ai_router.SessionLocal", side_effect=Exception("DB down")):
            provider, key, tier = self.router._get_user_config("user-err")

        assert provider == "gemini"
        assert key is None
        assert tier == "trial"


# ============================================================================
# Generate Tests (mocked providers)
# ============================================================================


class TestGenerate:
    """Test generate() — dispatches to correct provider with mocks."""

    def setup_method(self):
        self.router = AIRouter()

    def test_generate_calls_gemini_for_trial_user(self):
        mock_result = {"content": "Hello!", "provider": "gemini", "model": "gemini-1.5-flash"}

        with patch.object(self.router, "_get_user_config", return_value=("gemini", None, "trial")), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u1", "system", "hello"))

        assert result["provider"] == "gemini"
        assert result["content"] == "Hello!"

    def test_generate_calls_groq_for_groq_user(self):
        mock_result = {"content": "Hi!", "provider": "groq", "model": "llama-3.1-8b-instant"}

        with patch.object(self.router, "_get_user_config", return_value=("groq", None, "trial")), \
             patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u2", "system", "hello"))

        assert result["provider"] == "groq"

    def test_generate_forces_gemini_when_trial_picks_openai(self):
        mock_result = {"content": "Forced!", "provider": "gemini", "model": "gemini-1.5-flash"}

        with patch.object(self.router, "_get_user_config", return_value=("openai", "sk-key", "trial")), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u3", "system", "hello"))

        # Should have been forced to gemini, not openai
        assert result["provider"] == "gemini"

    def test_generate_allows_openai_for_tier2(self):
        mock_result = {"content": "GPT!", "provider": "openai", "model": "gpt-4o"}

        with patch.object(self.router, "_get_user_config", return_value=("openai", "sk-key", "tier2")), \
             patch.object(self.router, "_call_openai", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u4", "system", "hello"))

        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"

    def test_generate_allows_claude_for_tier3(self):
        mock_result = {"content": "Claude!", "provider": "claude", "model": "claude-sonnet-4-5"}

        with patch.object(self.router, "_get_user_config", return_value=("claude", "sk-ant-key", "tier3")), \
             patch.object(self.router, "_call_claude", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.generate("u5", "system", "hello"))

        assert result["provider"] == "claude"


# ============================================================================
# Fallback Tests
# ============================================================================


class TestFallback:
    """Test generate() fallback when primary provider fails."""

    def setup_method(self):
        self.router = AIRouter()

    def test_fallback_to_groq_when_gemini_fails(self):
        fallback_result = {"content": "Fallback!", "provider": "groq", "model": "llama-3.1-8b-instant"}

        with patch.object(self.router, "_get_user_config", return_value=("gemini", None, "trial")), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "key", "GROQ_API_KEY": "key2"}), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, side_effect=Exception("Gemini down")), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, return_value=fallback_result):

            result = _run(self.router.generate("u1", "system", "hello"))

        assert result["provider"] == "groq"
        assert result["fallback"] is True
        assert result["original_provider"] == "gemini"

    def test_fallback_to_gemini_when_groq_fails(self):
        fallback_result = {"content": "Fallback!", "provider": "gemini", "model": "gemini-1.5-flash"}

        with patch.object(self.router, "_get_user_config", return_value=("groq", None, "trial")), \
             patch.dict(os.environ, {"GROQ_API_KEY": "key", "GEMINI_API_KEY": "key2"}), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, side_effect=Exception("Groq down")), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, return_value=fallback_result):

            result = _run(self.router.generate("u2", "system", "hello"))

        assert result["provider"] == "gemini"
        assert result["fallback"] is True
        assert result["original_provider"] == "groq"

    def test_fallback_to_groq_when_openai_fails_for_paid_user(self):
        fallback_result = {"content": "Fallback!", "provider": "groq", "model": "llama-3.1-70b-versatile"}

        with patch.object(self.router, "_get_user_config", return_value=("openai", "sk-key", "tier2")), \
             patch.dict(os.environ, {"GROQ_API_KEY": "key"}), \
             patch.object(self.router, "_call_openai", new_callable=AsyncMock, side_effect=Exception("OpenAI down")), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, return_value=fallback_result):

            result = _run(self.router.generate("u3", "system", "hello"))

        assert result["fallback"] is True

    def test_both_providers_fail_returns_error(self):
        with patch.object(self.router, "_get_user_config", return_value=("gemini", None, "trial")), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "key", "GROQ_API_KEY": "key2"}), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, side_effect=Exception("Gemini down")), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, side_effect=Exception("Groq down")):

            result = _run(self.router.generate("u4", "system", "hello"))

        assert result["provider"] == "none"
        assert result["model"] == "none"
        assert "error" in result
        assert "unable to process" in result["content"].lower()


# ============================================================================
# Groq Retry Tests
# ============================================================================


class TestGroqRetry:
    """Test _call_groq_with_retry — exponential backoff on rate limits."""

    def setup_method(self):
        self.router = AIRouter()

    def test_succeeds_on_first_attempt(self):
        mock_result = {"content": "OK", "provider": "groq", "model": "llama-3.1-8b-instant"}

        with patch.object(self.router, "_call_groq", new_callable=AsyncMock, return_value=mock_result):
            result = _run(self.router._call_groq_with_retry(
                "system", "hello", "key", "llama-3.1-8b-instant", 100, 0.5,
            ))

        assert result["provider"] == "groq"

    def test_retries_on_rate_limit_then_succeeds(self):
        mock_result = {"content": "OK", "provider": "groq", "model": "llama-3.1-8b-instant"}

        with patch.object(
            self.router, "_call_groq", new_callable=AsyncMock,
            side_effect=[Exception("rate_limit_exceeded"), mock_result],
        ), patch("config.ai_router.time.sleep") as mock_sleep:
            result = _run(self.router._call_groq_with_retry(
                "system", "hello", "key", "llama-3.1-8b-instant", 100, 0.5,
            ))

        assert result["provider"] == "groq"
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    def test_retries_twice_on_rate_limit_then_succeeds(self):
        mock_result = {"content": "OK", "provider": "groq", "model": "llama-3.1-8b-instant"}

        with patch.object(
            self.router, "_call_groq", new_callable=AsyncMock,
            side_effect=[
                Exception("rate_limit_exceeded"),
                Exception("rate_limit_exceeded"),
                mock_result,
            ],
        ), patch("config.ai_router.time.sleep") as mock_sleep:
            result = _run(self.router._call_groq_with_retry(
                "system", "hello", "key", "llama-3.1-8b-instant", 100, 0.5,
            ))

        assert result["provider"] == "groq"
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)   # 2^0
        mock_sleep.assert_any_call(2)   # 2^1

    def test_gives_up_after_three_rate_limits(self):
        with patch.object(
            self.router, "_call_groq", new_callable=AsyncMock,
            side_effect=Exception("rate_limit_exceeded"),
        ), patch("config.ai_router.time.sleep"):
            try:
                _run(self.router._call_groq_with_retry(
                    "system", "hello", "key", "llama-3.1-8b-instant", 100, 0.5,
                ))
                assert False, "Should have raised"
            except Exception as exc:
                assert "rate_limit" in str(exc).lower()

    def test_non_rate_limit_error_not_retried(self):
        with patch.object(
            self.router, "_call_groq", new_callable=AsyncMock,
            side_effect=Exception("authentication_error: invalid key"),
        ), patch("config.ai_router.time.sleep") as mock_sleep:
            try:
                _run(self.router._call_groq_with_retry(
                    "system", "hello", "key", "llama-3.1-8b-instant", 100, 0.5,
                ))
                assert False, "Should have raised"
            except Exception as exc:
                assert "authentication_error" in str(exc)

        mock_sleep.assert_not_called()


# ============================================================================
# Health Check Tests
# ============================================================================


class TestCheckProvider:
    """Test check_provider() — health check for a provider."""

    def setup_method(self):
        self.router = AIRouter()

    def test_healthy_provider(self):
        mock_result = {"content": "Hello", "provider": "gemini", "model": "gemini-1.5-flash"}

        with patch.dict(os.environ, {"GEMINI_API_KEY": "key"}), \
             patch.object(self.router, "_call_gemini", new_callable=AsyncMock, return_value=mock_result):

            result = _run(self.router.check_provider("gemini"))

        assert result["status"] == "healthy"
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-1.5-flash"

    def test_unhealthy_provider(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "key"}), \
             patch.object(self.router, "_call_groq", new_callable=AsyncMock, side_effect=Exception("timeout")):

            result = _run(self.router.check_provider("groq"))

        assert result["status"] == "error"
        assert result["provider"] == "groq"
        assert "timeout" in result["error"]

    def test_unknown_provider(self):
        result = _run(self.router.check_provider("unknown_provider"))
        assert result["status"] == "error"
        assert "Unknown provider" in result["error"]

    def test_missing_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            result = _run(self.router.check_provider("gemini"))

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

    def test_free_providers_are_subset_of_all(self):
        assert self.router.FREE_PROVIDERS.issubset(set(self.router.PROVIDER_MAP.keys()))

    def test_four_providers_registered(self):
        assert len(self.router.PROVIDER_MAP) == 4
        assert set(self.router.PROVIDER_MAP.keys()) == {"gemini", "groq", "openai", "claude"}
