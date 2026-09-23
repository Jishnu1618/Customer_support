"""
LLM Provider Abstraction Layer
"""
import os
from typing import Optional
from configs.settings import settings

MAX_TOKENS = 1024  # Max output tokens for LLM judge calls


class LLMClient:
    """
    Client wrapper for interacting with the configured LLM provider.
    Supports Groq (via OpenAI-compatible API), OpenAI, Gemini, and Anthropic.
    """
    _groq_key_index: int = 0

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or settings.llm_provider).lower()
        self.model = model or settings.llm_model

    def generate_reply(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[str] = None,
    ) -> str:
        """
        Generates text using the configured provider.
        """
        if self.provider == "groq":
            keys = [
                k for k in getattr(settings, "groq_api_keys", [])
                if k and "your_" not in k
            ]
            if not keys:
                single_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
                if single_key and "your_" not in single_key:
                    keys = [single_key]

            if not keys:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."

            from openai import OpenAI

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format == "json" or ('"relevance"' in prompt and '"grounding"' in prompt):
                kwargs["response_format"] = {"type": "json_object"}

            last_exc = None
            total_keys = len(keys)
            # Try rotating across available keys if a rate limit (429) is encountered
            for attempt_idx in range(total_keys):
                key_idx = (LLMClient._groq_key_index + attempt_idx) % total_keys
                api_key = keys[key_idx]
                masked_key = f"{api_key[:8]}...{api_key[-4:]}"
                client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key,
                )
                try:
                    response = client.chat.completions.create(**kwargs)
                    # On success, advance rotation index for the next call to distribute load evenly
                    LLMClient._groq_key_index = (key_idx + 1) % total_keys
                    return response.choices[0].message.content or ""
                except Exception as exc:
                    exc_str = str(exc)
                    is_rate_limit = (
                        "rate_limit" in exc_str.lower()
                        or "429" in exc_str
                        or "resource_exhausted" in exc_str.lower()
                        or "quota" in exc_str.lower()
                    )
                    last_exc = exc
                    if is_rate_limit and total_keys > 1 and attempt_idx < total_keys - 1:
                        next_key_idx = (key_idx + 1) % total_keys
                        next_masked = f"{keys[next_key_idx][:8]}...{keys[next_key_idx][-4:]}"
                        print(f"  [KEY ROTATE] Key {masked_key} hit limit; rotating immediately to {next_masked}", flush=True)
                        continue
                    else:
                        raise exc

            if last_exc:
                raise last_exc
            return ""

        elif self.provider == "openai":
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        elif self.provider == "anthropic":
            api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            kwargs = {
                "model": self.model,
                "max_tokens": 1024,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            return response.content[0].text if response.content else ""

        elif self.provider in ("gemini", "google"):
            api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if not api_key or "your_" in api_key:
                return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # Determine response mime type
            is_json = (
                response_format == "json"
                or ('"relevance"' in prompt and '"grounding"' in prompt)
                or ('json' in prompt.lower() and '{' in prompt and '}' in prompt)
            )

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=4096,
                response_mime_type="application/json" if is_json else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                system_instruction=system_prompt if system_prompt else None,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""

        else:
            return f"[Mock Response from {self.provider}:{self.model}] Prompt processed successfully."
