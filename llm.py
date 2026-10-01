"""Minimal LLM client. Replaceable; no LangChain/LlamaIndex.

Uses OpenAI-compatible Chat Completions over HTTPS.
API key: CODEATLAS_LLM_API_KEY
Optional: CODEATLAS_LLM_BASE_URL, CODEATLAS_LLM_MODEL
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from config import (
    LLM_API_KEY_ENV,
    LLM_BASE_URL_ENV,
    LLM_DEFAULT_BASE_URL,
    LLM_DEFAULT_MODEL,
    LLM_MODEL_ENV,
    LLM_TIMEOUT_SECONDS,
)


class LLMNotConfigured(Exception):
    pass


class LLMError(Exception):
    pass


def complete_chat(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get(LLM_API_KEY_ENV, "").strip()
    if not api_key:
        raise LLMNotConfigured(
            f"{LLM_API_KEY_ENV} is not set. Configure an API key to use Ask CodeAtlas."
        )

    base_url = os.environ.get(LLM_BASE_URL_ENV, LLM_DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get(LLM_MODEL_ENV, LLM_DEFAULT_MODEL)
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LLMError(f"LLM request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError("Could not reach the LLM provider.") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("LLM response was missing message content.") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError("LLM returned an empty answer.")
    return content.strip()
