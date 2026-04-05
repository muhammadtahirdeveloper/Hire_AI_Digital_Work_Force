"""Central AI Router for all LLM calls.

Routes all requests to Anthropic Claude models based on user tier:
  - Free (trial, tier1): Claude Haiku
  - Professional (tier2): Claude Haiku
  - Enterprise (tier3): Claude Sonnet

Usage::

    router = AIRouter()
    result = await router.generate(
        user_id="usr_123",
        system_prompt="You are an email assistant.",
        user_message="Classify this email...",
    )
    print(result["content"], result["provider"], result["model"])
"""

import hashlib
import json
import logging
import os
import time
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Redis cache helper (lazy-init, optional)
# ------------------------------------------------------------------ #

_redis_client = None
_redis_checked = False
_CACHE_TTL = 3600  # 1 hour
_CONFIG_CACHE_TTL = 300  # 5 minutes


def _get_redis():
    """Get Redis client (lazy init, returns None if unavailable)."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis
        from config.settings import REDIS_URL
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logger.info("AI Router: Redis cache connected")
    except Exception as exc:
        logger.warning("AI Router: Redis unavailable, caching disabled: %s", exc)
        _redis_client = None
    return _redis_client


def _cache_key(prefix: str, *parts: str) -> str:
    """Build a deterministic cache key."""
    raw = ":".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"hireai:{prefix}:{h}"


class AIRouter:
    """Central router for all AI/LLM calls.

    Routes all requests to Anthropic Claude models.
    """

    PROVIDER_MAP = {
        "claude": "_call_claude",
    }

    # All providers are managed by HireAI
    MANAGED_PROVIDERS = {"claude"}

    # No BYOK providers
    BYOK_PROVIDERS = set()

    # Tiers that can use Claude Sonnet (paid)
    PAID_TIERS = {"tier2", "tier3"}

    # Default provider per tier — all Claude
    TIER_DEFAULTS = {
        "trial": "claude",
        "tier1": "claude",
        "tier2": "claude",
        "tier3": "claude",
    }

    # Tier-based model selection — Claude only
    PROVIDER_MODELS = {
        "claude": {
            "default": "claude-3-5-haiku-latest",
            "trial": "claude-3-5-haiku-latest",
            "tier1": "claude-3-5-haiku-latest",
            "tier2": "claude-3-5-haiku-latest",
            "tier3": "claude-sonnet-4-5-20250514",
        },
    }

    # Env var name for API key
    _ENV_MAP = {
        "claude": "ANTHROPIC_API_KEY",
    }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        user_id: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> dict:
        """Main entry point. Returns {"content", "provider", "model"}.

        Loads the user's configured tier, resolves the API key,
        and calls Claude with the appropriate model.

        Includes Redis caching: identical (system_prompt, user_message)
        pairs return cached results for 1 hour.
        """
        # 1. Load user config from user_agents table (with cache)
        _provider, _api_key, tier = self._get_user_config(user_id)

        # 2. Always use Claude
        provider = "claude"

        # 3. Resolve API key
        resolved_key = self._resolve_key(provider, None)

        # 4. Get correct model for tier
        model = self._get_model(provider, tier)

        # 4b. Check Redis cache for identical request
        r = _get_redis()
        cache_k = _cache_key("ai", provider, model, system_prompt, user_message)
        if r:
            try:
                cached = r.get(cache_k)
                if cached:
                    result = json.loads(cached)
                    result["cached"] = True
                    logger.debug("AI cache hit for key=%s", cache_k)
                    return result
            except Exception:
                pass

        # 5. Call Claude
        try:
            result = await self._call_claude(
                system_prompt, user_message, resolved_key, model,
                max_tokens, temperature,
            )
            # Store in cache
            if r:
                try:
                    r.setex(cache_k, _CACHE_TTL, json.dumps(result))
                except Exception:
                    pass
            return result
        except Exception as exc:
            logger.error("Claude failed: %s", exc)
            return {
                "content": (
                    "I apologize, but I'm unable to process this "
                    "request right now. Please try again later."
                ),
                "provider": "none",
                "model": "none",
                "error": str(exc),
            }

    async def check_provider(self, provider: str = "claude") -> dict:
        """Test if Claude is reachable and responding."""
        try:
            key = self._resolve_key("claude", None)
            model = self._get_model("claude", "trial")
            result = await self._call_claude(
                "You are a test assistant.", "Say hello in one word.",
                key, model, 10, 0.1,
            )
            return {"provider": "claude", "status": "healthy", "model": result["model"]}
        except Exception as exc:
            return {"provider": "claude", "status": "error", "error": str(exc)}

    # ------------------------------------------------------------------ #
    # Config helpers
    # ------------------------------------------------------------------ #

    def _get_user_config(self, user_id: str) -> tuple:
        """Read ai_provider, ai_api_key, tier from user_agents table.

        Caches in Redis for 5 minutes to reduce DB queries.

        Returns:
            (provider, byok_key_or_none, tier)
        """
        # Check Redis cache first
        r = _get_redis()
        config_key = f"hireai:ucfg:{user_id}"
        if r:
            try:
                cached = r.get(config_key)
                if cached:
                    data = json.loads(cached)
                    return ("claude", data.get("key"), data["tier"])
            except Exception:
                pass

        try:
            db = SessionLocal()
            try:
                row = db.execute(
                    text(
                        "SELECT ai_provider, ai_api_key, tier "
                        "FROM user_agents WHERE user_id = :uid"
                    ),
                    {"uid": user_id},
                ).fetchone()
                if row:
                    result = ("claude", row[1], row[2] or "trial")
                    # Cache (don't cache API keys for security — only provider+tier)
                    if r:
                        try:
                            r.setex(config_key, _CONFIG_CACHE_TTL, json.dumps({
                                "provider": "claude",
                                "tier": result[2],
                            }))
                        except Exception:
                            pass
                    return result
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Could not load user config: %s", exc)
        return ("claude", None, "trial")

    def _enforce_tier(self, provider: str, tier: str) -> str:
        """Always returns claude."""
        return "claude"

    def _resolve_key(self, provider: str, byok_key: Optional[str] = None) -> str:
        """Resolve the Anthropic API key from environment."""
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "No API key for Claude. Set ANTHROPIC_API_KEY env var."
            )
        return key

    def _get_model(self, provider: str, tier: str) -> str:
        """Get the correct Claude model name for a tier."""
        models = self.PROVIDER_MODELS.get("claude", {})
        return models.get(tier, models.get("default", "claude-3-5-haiku-latest"))

    # ------------------------------------------------------------------ #
    # Provider implementation — Claude only
    # ------------------------------------------------------------------ #

    async def _call_claude(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call Anthropic Claude API with rate-limit retry (max 3 attempts)."""
        from anthropic import Anthropic

        for attempt in range(3):
            try:
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                return {
                    "content": response.content[0].text,
                    "provider": "claude",
                    "model": model,
                }
            except Exception as exc:
                if "rate_limit" in str(exc).lower() and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning("Claude rate limited, retry in %ds (attempt %d/3)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                raise
