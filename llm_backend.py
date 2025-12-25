# llm_backend.py
# chat(): main entrypoint for all LLM calls in this project.
# Inputs: OpenAI-style messages
# Output: plain text response
# Keeping this centralized avoids Gemini SDK usage leaking into agents/supervisor.

from __future__ import annotations

import os
from typing import List, Dict

# load_dotenv() makes local dev easy: it loads GEMINI_API_KEY from .env when running scripts
from dotenv import load_dotenv
from google import genai


class GeminiBackend:
    """
    LLM backend adapter (Gemini implementation).

    Input:
      - OpenAI-style messages: [{"role": "...", "content": "..."}]

    Output:
      - Plain text response (str)

    Why it exists:
      - Keep Gemini SDK details in one place
      - Let Supervisor/Agents stay model-agnostic
    """
# __init__ runs once when the backend is created:
# - loads .env (local dev)
# - reads GEMINI_API_KEY
# - creates the Gemini client
# This prevents repeating setup work on every LLM call.

    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        # Load .env if present (safe to call multiple times)
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not set. Add it to .env (or export it) and retry."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

# Convert our internal message format into one prompt string (simple + portable for MVP)
# Call Gemini's generate_content and return resp.text as a plain string
# getattr is defensive: if SDK response shape changes, we still return something readable
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        prompt = self._messages_to_prompt(messages)

        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"temperature": temperature},
        )

        text = getattr(resp, "text", None)
        return (text or str(resp)).strip()

# Gemini can accept plain text prompts; we keep OpenAI-style messages internally
# and translate them here for portability and readability.
    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        """
        Simple role-preserving formatter.
        MVP-friendly; later we can use richer structured content.
        """
        chunks = []
        for m in messages:
            role = (m.get("role") or "user").upper()
            content = m.get("content") or ""
            chunks.append(f"{role}:\n{content}")
        return "\n\n".join(chunks)
