"""Model adapter layer — unified interface for calling AI models.

Supported providers:
- OpenAI (GPT-4o, o1, o3, o4)
- Anthropic (Claude)
- Google (Gemini)
- xAI (Grok)
- Mistral
- Together AI (Meta Llama)
- Local (Ollama)
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    text: str
    latency_ms: float
    model_name: str
    error: bool = False


class ModelAdapter(ABC):
    @abstractmethod
    def call(self, prompt: str) -> ModelResponse: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class OpenAIAdapter(ModelAdapter):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        from openai import OpenAI

        self._model = model
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=key)

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.choices[0].message.content or "", latency_ms=latency, model_name=self.name)


class AnthropicAdapter(ModelAdapter):
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        import anthropic

        self._model = model
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=key)

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.content[0].text if resp.content else "", latency_ms=latency, model_name=self.name)


class GoogleAdapter(ModelAdapter):
    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None):
        import google.generativeai as genai

        self._model_name = model
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model)

    @property
    def name(self) -> str:
        return self._model_name

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._model.generate_content(prompt)
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.text or "", latency_ms=latency, model_name=self.name)


class XAIAdapter(ModelAdapter):
    """xAI (Grok) — OpenAI-compatible API at api.x.ai."""

    def __init__(self, model: str = "grok-3-mini", api_key: str | None = None):
        from openai import OpenAI

        self._model = model
        key = api_key or os.environ.get("XAI_API_KEY")
        if not key:
            raise ValueError("XAI_API_KEY not set")
        self._client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.choices[0].message.content or "", latency_ms=latency, model_name=self.name)


class MistralAdapter(ModelAdapter):
    """Mistral AI — uses the mistralai Python SDK."""

    def __init__(self, model: str = "mistral-large-latest", api_key: str | None = None):
        from mistralai import Mistral

        self._model = model
        key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not key:
            raise ValueError("MISTRAL_API_KEY not set")
        self._client = Mistral(api_key=key)

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat.complete(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        text = resp.choices[0].message.content if resp.choices else ""
        return ModelResponse(text=text or "", latency_ms=latency, model_name=self.name)


class TogetherAdapter(ModelAdapter):
    """Together AI — hosts Meta Llama and other open models. OpenAI-compatible API."""

    def __init__(self, model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo", api_key: str | None = None):
        from openai import OpenAI

        self._model = model
        key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not key:
            raise ValueError("TOGETHER_API_KEY not set")
        self._client = OpenAI(api_key=key, base_url="https://api.together.xyz/v1")

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.choices[0].message.content or "", latency_ms=latency, model_name=self.name)


class LocalModelAdapter(ModelAdapter):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434/v1"):
        from openai import OpenAI

        self._model = model
        self._client = OpenAI(base_url=base_url, api_key="not-needed")

    @property
    def name(self) -> str:
        return f"local/{self._model}"

    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.choices[0].message.content or "", latency_ms=latency, model_name=self.name)


# ── Registry ──────────────────────────────────────────────────────────

ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleAdapter,
    "xai": XAIAdapter,
    "mistral": MistralAdapter,
    "together": TogetherAdapter,
    "local": LocalModelAdapter,
}

_PROVIDER_MAP = {
    "gpt-": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "claude-": "anthropic",
    "gemini-": "google",
    "grok-": "xai",
    "mistral-": "mistral",
    "meta-llama/": "together",
    "llama-": "together",
    "local/": "local",
}

# Estimated cost per 100 questions (USD) — ~200 input + ~200 output tokens each
MODEL_COST_PER_100: dict[str, float] = {
    "gpt-4o": 0.25,
    "gpt-4o-mini": 0.01,
    "o1": 3.00,
    "o3": 2.00,
    "claude-opus-4-6": 1.80,
    "claude-sonnet-4-6": 0.36,
    "claude-sonnet-4-20250514": 0.36,
    "claude-haiku-4-5-20251001": 0.05,
    "gemini-2.5-pro": 0.25,
    "gemini-2.5-flash": 0.02,
    "gemini-2.0-flash": 0.01,
    "grok-3-mini": 0.02,
    "mistral-large-latest": 0.16,
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": 0.04,
}


def get_adapter(provider: str, **kwargs) -> ModelAdapter:
    cls = ADAPTER_REGISTRY.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider '{provider}'. Available: {list(ADAPTER_REGISTRY)}")
    return cls(**kwargs)


def resolve_provider(model_name: str) -> str | None:
    for prefix, prov in _PROVIDER_MAP.items():
        if model_name.startswith(prefix):
            return prov
    return None


def get_cost_per_100(model_name: str) -> float | None:
    """Return estimated cost per 100 questions, or None if unknown."""
    return MODEL_COST_PER_100.get(model_name)


def call_model(model_name: str, prompt: str, _adapter_cache: dict | None = None, **kwargs) -> ModelResponse:
    """Resolve provider, reuse cached adapter, call model with retries."""
    provider = resolve_provider(model_name)
    if provider is None:
        raise ValueError(f"Cannot infer provider for model '{model_name}'")

    if _adapter_cache is not None and model_name in _adapter_cache:
        adapter = _adapter_cache[model_name]
    else:
        model_kwarg = model_name.removeprefix("local/") if provider == "local" else model_name
        adapter = get_adapter(provider, model=model_kwarg, **kwargs)
        if _adapter_cache is not None:
            _adapter_cache[model_name] = adapter

    try:
        return adapter.call(prompt)
    except Exception as e:
        logger.error("Model call failed for %s after retries: %s", model_name, e)
        return ModelResponse(text="", latency_ms=0.0, model_name=model_name, error=True)
