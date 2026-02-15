# utils/openai_client.py
"""
OpenAI API Key Rotation & LLM Factory

Distributes parallel LLM calls across multiple API keys to:
- Increase effective rate limits (each key has its own quota)
- Reduce risk of hitting per-key rate limits during parallel processing
- Provide redundancy if one key is temporarily throttled

SETUP:
  In Railway (or .env), set comma-separated keys:
    OPENAI_API_KEYS=sk-abc123,sk-def456,sk-ghi789

  Falls back to single OPENAI_API_KEY if OPENAI_API_KEYS is not set.

USAGE:
  from utils.openai_client import get_openai_llm

  # Each call returns a ChatOpenAI bound to the next key in rotation
  llm = get_openai_llm(model="gpt-4o", temperature=0, json_mode=True)
  response = await (prompt | llm | parser).ainvoke({...})
"""

import os
import threading
from typing import Optional
from langchain_openai import ChatOpenAI

from utils.logger import fact_logger


class OpenAIKeyRotator:
    """
    Thread-safe round-robin API key rotator.
    
    Each call to next_key() returns the next key in the pool,
    cycling back to the start after reaching the end.
    """

    def __init__(self):
        self._keys = []
        self._index = 0
        self._lock = threading.Lock()
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment variables."""
        # Primary source: comma-separated list
        keys_str = os.getenv("OPENAI_API_KEYS", "").strip()
        if keys_str:
            self._keys = [k.strip() for k in keys_str.split(",") if k.strip()]

        # Fallback: single key
        if not self._keys:
            single_key = os.getenv("OPENAI_API_KEY", "").strip()
            if single_key:
                self._keys = [single_key]

        if not self._keys:
            fact_logger.logger.error(
                "No OpenAI API keys found. "
                "Set OPENAI_API_KEYS (comma-separated) or OPENAI_API_KEY."
            )
        else:
            fact_logger.logger.info(
                f"OpenAI key rotator initialized with {len(self._keys)} key(s)"
            )

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def next_key(self) -> str:
        """
        Get the next API key in round-robin order.
        Thread-safe.
        """
        if not self._keys:
            raise ValueError(
                "No OpenAI API keys configured. "
                "Set OPENAI_API_KEYS or OPENAI_API_KEY."
            )

        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key


# ============================================================================
# Module-level singleton
# ============================================================================

_rotator: Optional[OpenAIKeyRotator] = None
_rotator_lock = threading.Lock()


def _get_rotator() -> OpenAIKeyRotator:
    """Lazy-init singleton rotator."""
    global _rotator
    if _rotator is None:
        with _rotator_lock:
            if _rotator is None:
                _rotator = OpenAIKeyRotator()
    return _rotator


# ============================================================================
# Public API
# ============================================================================

def get_openai_llm(
    model: str = "gpt-4o",
    temperature: float = 0,
    json_mode: bool = False,
    **kwargs
) -> ChatOpenAI:
    """
    Factory: return a ChatOpenAI instance using the next rotated API key.

    Call this each time you need an LLM instance -- especially inside
    parallel loops so that concurrent calls spread across different keys.

    Args:
        model: OpenAI model name (e.g. "gpt-4o", "gpt-4o-mini")
        temperature: Sampling temperature
        json_mode: If True, bind response_format={"type": "json_object"}
        **kwargs: Extra args forwarded to ChatOpenAI

    Returns:
        ChatOpenAI instance (optionally bound to JSON mode)

    Example:
        # In a parallel verification loop:
        async def verify_one_claim(claim):
            llm = get_openai_llm(model="gpt-4o", json_mode=True)
            chain = prompt | llm | parser
            return await chain.ainvoke({...})
    """
    rotator = _get_rotator()
    api_key = rotator.next_key()

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        **kwargs
    )

    if json_mode:
        llm = llm.bind(response_format={"type": "json_object"})

    return llm


def get_key_count() -> int:
    """Return how many API keys are available."""
    return _get_rotator().key_count
