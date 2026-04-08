"""Model adapter layer — unified interface for calling AI models.

Supported providers:
- OpenAI (GPT-4.1, GPT-4o, o3, o4-mini, GPT-5.4)
- Anthropic (Claude 4.6, 4.5, Haiku 4.5)
- Google (Gemini 2.5 Pro, 3.1 Pro, 3 Flash)
- xAI (Grok 3, Grok 4, Grok 4.20)
- Mistral (Mistral Large 3)
- Together AI (Meta Llama 4, Llama 3.3)
- DeepSeek (V4, R1) — OpenAI-compatible API
- Cohere (Command A, Command A Reasoning)
- Amazon Bedrock (Nova 2 Pro, Nova 2 Lite)
- Local (Ollama)
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

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
    """OpenAI models. Handles both standard (GPT) and reasoning (o-series) models.

    o-series models (o1, o3, o4-mini) use max_completion_tokens instead of
    max_tokens and do not support the temperature parameter.
    """

    # Prefixes that require max_completion_tokens instead of max_tokens
    _REASONING_PREFIXES = ("o1", "o3", "o4", "gpt-5")

    def __init__(self, model: str = "gpt-4.1", api_key: str | None = None):
        from openai import OpenAI

        self._model = model
        self._is_reasoning = any(model.startswith(p) for p in self._REASONING_PREFIXES)
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
        if self._is_reasoning:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1024,
            )
        else:
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


class DeepSeekAdapter(ModelAdapter):
    """DeepSeek — OpenAI-compatible API at api.deepseek.com.

    Supports both standard models (deepseek-chat/V4) and reasoning (deepseek-reasoner/R1).
    R1 uses max_completion_tokens like OpenAI reasoning models.
    """

    _REASONING_MODELS = ("deepseek-reasoner",)

    def __init__(self, model: str = "deepseek-chat", api_key: str | None = None):
        from openai import OpenAI

        self._model = model
        self._is_reasoning = model in self._REASONING_MODELS
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        self._client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        if self._is_reasoning:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1024,
            )
        else:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1024,
            )
        latency = (time.perf_counter() - start) * 1000
        return ModelResponse(text=resp.choices[0].message.content or "", latency_ms=latency, model_name=self.name)


class CohereAdapter(ModelAdapter):
    """Cohere — uses the cohere Python SDK (v2 client).

    Supports Command A Reasoning and Command R models.
    Reasoning models return [thinking, text] content items — we extract only the text.
    """

    def __init__(self, model: str = "command-a-reasoning-08-2025", api_key: str | None = None):
        import cohere

        self._model = model
        key = api_key or os.environ.get("COHERE_API_KEY")
        if not key:
            raise ValueError("COHERE_API_KEY not set")
        self._client = cohere.ClientV2(api_key=key)

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        latency = (time.perf_counter() - start) * 1000
        # Reasoning models return [thinking, text] items; extract only text
        text = ""
        if resp.message and resp.message.content:
            for item in resp.message.content:
                if getattr(item, "type", None) == "text":
                    text = item.text
                    break
            # Fallback for non-reasoning models that have .text directly
            if not text and hasattr(resp.message.content[0], "text"):
                text = resp.message.content[0].text
        return ModelResponse(text=text or "", latency_ms=latency, model_name=self.name)


class BedrockAdapter(ModelAdapter):
    """Amazon Bedrock — uses boto3 bedrock-runtime (Converse API).

    Supports Nova Premier, Nova 2 Lite, and other Bedrock-hosted models.
    Requires AWS credentials configured via environment or IAM role.

    Bedrock requires cross-region inference profile IDs (us.<model-id>)
    for on-demand invocation of newer models.
    """

    def __init__(self, model: str = "amazon.nova-premier-v1:0", api_key: str | None = None):
        import boto3

        self._model = model
        # Inference profile ID: prepend "us." for cross-region on-demand access
        self._inference_id = f"us.{model}" if not model.startswith("us.") else model
        region = os.environ.get("AWS_REGION", "us-east-1")
        self._client = boto3.client("bedrock-runtime", region_name=region)

    @property
    def name(self) -> str:
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def call(self, prompt: str) -> ModelResponse:
        start = time.perf_counter()
        resp = self._client.converse(
            modelId=self._inference_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0},
        )
        latency = (time.perf_counter() - start) * 1000
        text = ""
        if resp.get("output", {}).get("message", {}).get("content"):
            text = resp["output"]["message"]["content"][0].get("text", "")
        return ModelResponse(text=text or "", latency_ms=latency, model_name=self.name)


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
    "deepseek": DeepSeekAdapter,
    "cohere": CohereAdapter,
    "bedrock": BedrockAdapter,
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
    "deepseek-": "deepseek",
    "command-": "cohere",
    "amazon.nova-": "bedrock",
    "local/": "local",
}

# Estimated cost per 100 questions (USD) — ~200 input + ~200 output tokens each
MODEL_COST_PER_100: dict[str, float] = {
    # OpenAI
    "gpt-4.1": 0.16,           # $2/$8 per 1M tokens
    "gpt-4.1-mini": 0.03,      # $0.40/$1.60 per 1M tokens
    "gpt-4.1-nano": 0.01,      # $0.10/$0.40 per 1M tokens
    "gpt-4o": 0.25,            # $2.50/$10 per 1M tokens
    "gpt-4o-mini": 0.01,
    "o1": 3.00,
    "o3": 2.00,                # $2/$8 per 1M tokens (reasoning)
    "o4-mini": 0.22,           # $1.10/$4.40 per 1M tokens (reasoning)
    "gpt-5.4": 2.00,           # reasoning model
    "gpt-5.4-mini": 0.10,     # $0.75/$4.50 per 1M tokens
    "gpt-5": 1.50,             # reasoning model
    "gpt-5-mini": 0.15,        # reasoning model
    # Anthropic
    "claude-opus-4-6": 1.80,   # $15/$75 per 1M tokens
    "claude-sonnet-4-6": 0.36, # $3/$15 per 1M tokens
    "claude-opus-4-20250514": 1.80,
    "claude-sonnet-4-20250514": 0.36,
    "claude-haiku-4-5-20251001": 0.05,
    # Google
    "gemini-2.5-pro": 0.25,
    "gemini-2.5-flash": 0.02,
    "gemini-2.0-flash": 0.01,
    "gemini-3-flash-preview": 0.07,  # $0.50/$3.00 per 1M tokens
    # xAI
    "grok-3": 0.36,            # $3/$15 per 1M tokens
    "grok-3-mini": 0.02,       # $0.30/$0.50 per 1M tokens
    "grok-4": 0.36,            # $3/$15 per 1M tokens
    "grok-4.20-0309-non-reasoning": 0.16, # $2/$6 per 1M tokens
    "grok-4.20-0309-reasoning": 0.16,     # $2/$6 per 1M tokens
    # Mistral
    "mistral-large-latest": 0.16,
    # Meta / Together
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": 0.04,
    # DeepSeek
    "deepseek-chat": 0.01,             # V4: $0.30/$0.50 per 1M tokens
    "deepseek-reasoner": 0.05,         # R1: $0.55/$2.00 per 1M tokens
    # Cohere
    "command-a-reasoning-08-2025": 0.25, # Command A Reasoning: $2.50/$10 per 1M tokens
    "command-r-08-2024": 0.02,          # Command R: $0.15/$0.60 per 1M tokens
    # Amazon Bedrock (Nova 2)
    "amazon.nova-pro-v1:0": 0.16,      # Nova Pro: $0.80/$3.20 per 1M tokens
    "amazon.nova-2-lite-v1:0": 0.06,  # Nova 2 Lite: $0.30/$2.50 per 1M tokens
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
