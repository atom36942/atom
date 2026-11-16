# import
import json
from typing import Any

# function
async def func_anthropic_json(*, client_anthropic: Any, content: str | list, schema: dict, model: str = "claude-opus-5-5", max_tokens: int = 16000, system: str | None = None) -> dict:
    """Ask Claude for JSON that always matches schema (structured outputs). content is the user message: text, or content blocks (e.g. a base64 PDF document block, then a text block). A declined request is rerun on Anthropic's fallback model; if that declines too, returns {}."""
    if not client_anthropic: raise Exception("Claude client not initialized (config_anthropic_key)")
    kwargs = {"system": system} if system else {}
    response = await client_anthropic.beta.messages.create(model=model, max_tokens=max_tokens, betas=["server-side-fallback-2026-07-01"], fallbacks="default", output_config={"format": {"type": "json_schema", "schema": schema}}, messages=[{"role": "user", "content": content}], **kwargs)
    if response.stop_reason == "refusal": return {}
    if response.stop_reason == "max_tokens": raise Exception("Claude reply was cut off at max_tokens")
    text = next((block.text for block in response.content if block.type == "text"), "")
    return json.loads(text or "{}")
