"""func_anthropic_json asks Claude for schema-bound JSON with the server-side refusal fallback, returns {} when the whole chain declines, and refuses without a client."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from function.ai import func_anthropic_json

SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"name": {"type": "string"}}, "required": ["name"]}


def client(*, stop_reason="end_turn", text='{"name": "Asha"}'):
    response = SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)])
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response))))


class AnthropicJsonTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_the_json_and_sends_schema_and_fallback(self):
        c = client()
        self.assertEqual(await func_anthropic_json(client_anthropic=c, content="Extract the name", schema=SCHEMA), {"name": "Asha"})
        kwargs = c.beta.messages.create.await_args.kwargs
        self.assertEqual(kwargs["output_config"], {"format": {"type": "json_schema", "schema": SCHEMA}})
        self.assertEqual((kwargs["fallbacks"], kwargs["betas"]), ("default", ["server-side-fallback-2026-07-01"]))
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "Extract the name"}])
        self.assertNotIn("system", kwargs)

    async def test_refusal_returns_empty(self):
        self.assertEqual(await func_anthropic_json(client_anthropic=client(stop_reason="refusal", text=""), content="x", schema=SCHEMA), {})

    async def test_cut_off_reply_raises(self):
        with self.assertRaisesRegex(Exception, "max_tokens"): await func_anthropic_json(client_anthropic=client(stop_reason="max_tokens", text='{"na'), content="x", schema=SCHEMA)

    async def test_no_client_raises(self):
        with self.assertRaisesRegex(Exception, "config_anthropic_key"): await func_anthropic_json(client_anthropic=None, content="x", schema=SCHEMA)


if __name__ == "__main__":
    unittest.main()
