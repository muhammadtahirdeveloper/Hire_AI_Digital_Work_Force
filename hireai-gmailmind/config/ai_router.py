"""Central AI Router for all LLM calls.

Routes requests to the correct AI provider based on the user's tier:
  - Free (trial, tier1): Groq (Llama) — HireAI managed key
  - Professional (tier2): Claude Haiku — HireAI managed key
  - Enterprise (tier3): Claude Sonnet — HireAI managed key
  - OpenAI: only available with user's own API key (BYOK)

Usage::

    router = AIRouter()
    result = await router.generate(
        user_id="usr_123",
        system_prompt="You are an email assistant.",
        user_message="Classify this email...",
    )
    print(result["content"], result["provider"], result["model"])
"""

import logging
import os
import time
from typing import Optional

from sqlalchemy import text

from config.database import SessionLocal

logger = logging.getLogger(__name__)


class AIRouter:
    """Central router for all AI/LLM calls.

    Reads user's ai_provider from user_agents table,
    routes to correct provider, returns unified response.
    """

    PROVIDER_MAP = {
        "groq": "_call_groq_with_retry",
        "claude": "_call_claude",
        "openai": "_call_openai",
        "gemini": "_call_gemini",
    }

    # Managed providers (HireAI provides the key)
    MANAGED_PROVIDERS = {"groq", "claude"}

    # BYOK-only providers (user must provide their own key)
    BYOK_PROVIDERS = {"openai", "gemini"}

    # Tiers that can use Claude (paid)
    PAID_TIERS = {"tier2", "tier3"}

    # Default provider per tier (used when user has no preference)
    TIER_DEFAULTS = {
        "trial": "groq",
        "tier1": "groq",
        "tier2": "claude",
        "tier3": "claude",
    }

    # Tier-based model selection
    PROVIDER_MODELS = {
        "groq": {
            "default": "llama-3.1-8b-instant",
            "trial": "llama-3.1-8b-instant",
            "tier1": "llama-3.1-8b-instant",
            "tier2": "llama-3.1-70b-versatile",
            "tier3": "llama-3.1-70b-versatile",
        },
        "claude": {
            "default": "claude-3-5-haiku-latest",
            "trial": "claude-3-5-haiku-latest",
            "tier1": "claude-3-5-haiku-latest",
            "tier2": "claude-3-5-haiku-latest",
            "tier3": "claude-sonnet-4-5-20250514",
        },
        "openai": {
            "default": "gpt-4o-mini",
            "trial": "gpt-4o-mini",
            "tier1": "gpt-4o-mini",
            "tier2": "gpt-4o",
            "tier3": "gpt-4o",
        },
        "gemini": {
            "default": "gemini-2.0-flash",
            "trial": "gemini-2.0-flash",
            "tier1": "gemini-2.0-flash",
            "tier2": "gemini-1.5-pro",
            "tier3": "gemini-1.5-pro",
        },
    }

    # Env var name for each provider's managed API key
    _ENV_MAP = {
        "groq": "GROQ_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
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

        Loads the user's configured provider, enforces tier restrictions,
        resolves the API key, and calls the correct provider method.
        If the primary provider fails, falls back to an alternate free
        provider before giving up.
        """
        # 1. Load user config from user_agents table
        provider, api_key, tier = self._get_user_config(user_id)

        # 2. Enforce tier restrictions
        provider = self._enforce_tier(provider, tier)

        # 3. Resolve API key (BYOK or managed)
        resolved_key = self._resolve_key(provider, api_key)

        # 4. Get correct model for provider + tier
        model = self._get_model(provider, tier)

        # 5. Call the correct provider (with fallback on failure)
        try:
            method = getattr(self, self.PROVIDER_MAP[provider])
            result = await method(
                system_prompt, user_message, resolved_key, model,
                max_tokens, temperature,
            )
            return result
        except Exception as exc:
            logger.error("Provider %s failed: %s", provider, exc)

            # Fallback: try alternate managed provider
            fallback = "groq" if provider != "groq" else "claude"
            try:
                logger.info("Falling back to %s", fallback)
                fallback_key = self._resolve_key(fallback, None)
                fallback_model = self._get_model(fallback, tier)
                fallback_method = getattr(self, self.PROVIDER_MAP[fallback])
                result = await fallback_method(
                    system_prompt, user_message, fallback_key,
                    fallback_model, max_tokens, temperature,
                )
                result["fallback"] = True
                result["original_provider"] = provider
                return result
            except Exception as fallback_exc:
                logger.error("Fallback %s also failed: %s", fallback, fallback_exc)
                return {
                    "content": (
                        "I apologize, but I'm unable to process this "
                        "request right now. Please try again later."
                    ),
                    "provider": "none",
                    "model": "none",
                    "error": str(exc),
                }

    async def check_provider(self, provider: str) -> dict:
        """Test if a provider is reachable and responding."""
        if provider not in self.PROVIDER_MAP:
            return {"provider": provider, "status": "error", "error": "Unknown provider"}
        try:
            key = self._resolve_key(provider, None)
            model = self._get_model(provider, "trial")
            method = getattr(self, self.PROVIDER_MAP[provider])
            result = await method(
                "You are a test assistant.", "Say hello in one word.",
                key, model, 10, 0.1,
            )
            return {"provider": provider, "status": "healthy", "model": result["model"]}
        except Exception as exc:
            return {"provider": provider, "status": "error", "error": str(exc)}

    # ------------------------------------------------------------------ #
    # Config helpers
    # ------------------------------------------------------------------ #

    def _get_user_config(self, user_id: str) -> tuple:
        """Read ai_provider, ai_api_key, tier from user_agents table.

        Returns:
            (provider, byok_key_or_none, tier)
        """
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
                    return (row[0] or "groq", row[1], row[2] or "trial")
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Could not load user config: %s", exc)
        return ("groq", None, "trial")

    def _enforce_tier(self, provider: str, tier: str) -> str:
        """Route to correct provider based on tier.

        - trial/tier1: groq only (unless BYOK with own key)
        - tier2: claude (Haiku) by default
        - tier3: claude (Sonnet) by default
        - BYOK providers (openai, gemini) allowed for any tier if user has key
        """
        # If provider is BYOK-only, user must have provided a key — allow it
        # (key check happens later in _resolve_key)
        if provider in self.BYOK_PROVIDERS:
            return provider

        # Free tiers can only use groq
        if tier not in self.PAID_TIERS and provider != "groq":
            logger.warning(
                "User on tier=%s tried provider=%s, forcing groq",
                tier, provider,
            )
            return "groq"

        # Paid tiers: use their configured provider or tier default
        if provider not in self.PROVIDER_MAP:
            return self.TIER_DEFAULTS.get(tier, "groq")

        return provider

    def _resolve_key(self, provider: str, byok_key: Optional[str] = None) -> str:
        """Use BYOK key if provided, else fall back to env var."""
        if byok_key:
            return byok_key
        env_name = self._ENV_MAP.get(provider, "")
        key = os.environ.get(env_name, "")
        if not key:
            raise ValueError(
                f"No API key for provider={provider}. "
                f"Set {env_name} env var or provide a BYOK key."
            )
        return key

    def _get_model(self, provider: str, tier: str) -> str:
        """Get the correct model name for a provider + tier combination."""
        models = self.PROVIDER_MODELS.get(provider, {})
        return models.get(tier, models.get("default", "llama-3.1-8b-instant"))

    # ------------------------------------------------------------------ #
    # Provider implementations
    # ------------------------------------------------------------------ #

    async def _call_gemini(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call Google Gemini API."""
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        gm = genai.GenerativeModel(model)

        prompt = f"{system_prompt}\n\nUser message:\n{user_message}"
        response = gm.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return {
            "content": response.text,
            "provider": "gemini",
            "model": model,
        }

    async def _call_groq(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call Groq API (Llama models)."""
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return {
            "content": response.choices[0].message.content,
            "provider": "groq",
            "model": model,
        }

    async def _call_groq_with_retry(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call Groq with exponential backoff on rate-limit errors (max 3 attempts)."""
        for attempt in range(3):
            try:
                return await self._call_groq(
                    system_prompt, user_message, api_key, model,
                    max_tokens, temperature,
                )
            except Exception as exc:
                if "rate_limit" in str(exc).lower() and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning("Groq rate limited, retry in %ds (attempt %d/3)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                raise

    async def _call_openai(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call OpenAI API."""
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return {
            "content": response.choices[0].message.content,
            "provider": "openai",
            "model": model,
        }

    async def _call_claude(
        self, system_prompt: str, user_message: str,
        api_key: str, model: str,
        max_tokens: int, temperature: float,
    ) -> dict:
        """Call Anthropic Claude API."""
        from anthropic import Anthropic

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
