"""Unit tests verifying multi-key pooling, round-robin rotation, and 429 failover for GeminiProvider."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.ai.gateway.interface import LLMMessage, LLMOptions
from app.ai.providers.gemini_provider import GeminiProvider
from app.core.errors import ProviderUnavailableError


def test_gemini_provider_single_key():
    provider = GeminiProvider(api_key="key_single")
    assert provider.api_key == "key_single"
    assert provider.api_keys == ["key_single"]
    assert provider._get_next_api_key() == "key_single"
    assert provider._get_next_api_key() == "key_single"


def test_gemini_provider_comma_separated_keys():
    provider = GeminiProvider(api_key="key1, key2,  key3 ")
    assert provider.api_key == "key1"
    assert provider.api_keys == ["key1", "key2", "key3"]
    # Verify round robin rotation
    assert provider._get_next_api_key() == "key1"
    assert provider._get_next_api_key() == "key2"
    assert provider._get_next_api_key() == "key3"
    assert provider._get_next_api_key() == "key1"


def test_gemini_provider_list_keys():
    provider = GeminiProvider(api_key=["k1", "k2"])
    assert provider.api_key == "k1"
    assert provider.api_keys == ["k1", "k2"]
    assert provider._get_next_api_key() == "k1"
    assert provider._get_next_api_key() == "k2"
    assert provider._get_next_api_key() == "k1"


def test_gemini_provider_empty_key():
    provider = GeminiProvider(api_key="")
    assert provider.api_key == ""
    assert provider.api_keys == []
    assert provider._get_next_api_key() == ""


@pytest.mark.asyncio
async def test_gemini_generate_round_robin():
    """Verify that successive generate calls use different keys in the pool."""
    provider = GeminiProvider(api_key="key_alpha,key_beta")
    captured_urls = []

    async def mock_post(url, *args, **kwargs):
        captured_urls.append(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Hello world"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
        }
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        msg = [LLMMessage(role="user", content="Test")]
        opts = LLMOptions(model="gemini-1.5-flash")

        res1 = await provider.generate(msg, opts)
        assert res1.content == "Hello world"
        assert "key=key_alpha" in captured_urls[0]

        res2 = await provider.generate(msg, opts)
        assert res2.content == "Hello world"
        assert "key=key_beta" in captured_urls[1]

        res3 = await provider.generate(msg, opts)
        assert res3.content == "Hello world"
        assert "key=key_alpha" in captured_urls[2]


@pytest.mark.asyncio
async def test_gemini_429_auto_failover_to_next_key():
    """Verify that when key1 hits 429, the provider immediately fails over to key2."""
    provider = GeminiProvider(api_key="exhausted_key,healthy_key")
    captured_urls = []

    async def mock_post(url, *args, **kwargs):
        captured_urls.append(url)
        mock_resp = MagicMock()
        if "exhausted_key" in url:
            mock_resp.status_code = 429
            mock_resp.json.return_value = {"error": "Rate limit exceeded"}
        else:
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Generated successfully"}]}}],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 15}
            }
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        msg = [LLMMessage(role="user", content="Generate blog")]
        opts = LLMOptions(model="gemini-1.5-flash")

        res = await provider.generate(msg, opts)
        assert res.content == "Generated successfully"
        # First attempt tried exhausted_key, second attempt automatically used healthy_key
        assert len(captured_urls) == 2
        assert "exhausted_key" in captured_urls[0]
        assert "healthy_key" in captured_urls[1]
