"""Critical Provider Test Matrix verifying Scenarios A-E and Tests 1-5."""
import pytest
from app.ai.gateway.gateway import LLMGateway
from app.ai.gateway.interface import LLMMessage, LLMOptions
from app.ai.providers.mock_provider import MockProvider
from app.core.errors import NoProviderConfiguredError, ProviderUnavailableError


@pytest.mark.asyncio
async def test_matrix_test_1_openai_only():
    """Test 1 / Scenario A: Only OpenAI configured -> all operations use OpenAI."""
    gateway = LLMGateway()
    # Clear any auto-detected providers
    gateway._providers.clear()
    gateway._active_provider_name = None

    # Register only OpenAI
    openai_mock = MockProvider("OpenAI")
    gateway.register_provider(openai_mock, make_active=True)

    assert gateway.is_operational() is True
    assert gateway.active_provider_name == "OpenAI"
    assert gateway.get_configured_providers() == ["OpenAI"]

    # Execute generation
    resp = await gateway.generate([LLMMessage(role="user", content="Write intro")])
    assert resp.provider == "OpenAI"
    assert len(openai_mock.call_history) == 1


@pytest.mark.asyncio
async def test_matrix_test_2_gemini_only():
    """Test 2 / Scenario B: Only Gemini configured -> all operations use Gemini."""
    gateway = LLMGateway()
    gateway._providers.clear()
    gateway._active_provider_name = None

    gemini_mock = MockProvider("Gemini")
    gateway.register_provider(gemini_mock, make_active=True)

    assert gateway.is_operational() is True
    assert gateway.active_provider_name == "Gemini"
    assert gateway.get_configured_providers() == ["Gemini"]

    resp = await gateway.generate([LLMMessage(role="user", content="Write outline")])
    assert resp.provider == "Gemini"
    assert len(gemini_mock.call_history) == 1


@pytest.mark.asyncio
async def test_matrix_test_3_claude_only():
    """Test 3 / Scenario C: Only Claude configured -> all operations use Claude."""
    gateway = LLMGateway()
    gateway._providers.clear()
    gateway._active_provider_name = None

    claude_mock = MockProvider("Claude")
    gateway.register_provider(claude_mock, make_active=True)

    assert gateway.is_operational() is True
    assert gateway.active_provider_name == "Claude"
    assert gateway.get_configured_providers() == ["Claude"]

    resp = await gateway.generate([LLMMessage(role="user", content="Fact check claim")])
    assert resp.provider == "Claude"
    assert len(claude_mock.call_history) == 1


@pytest.mark.asyncio
async def test_matrix_test_4_multiple_providers_active_selection():
    """Test 4 / Scenario D & E: OpenAI + Gemini + Claude configured -> Admin selects active."""
    gateway = LLMGateway()
    gateway._providers.clear()
    gateway._active_provider_name = None

    openai_mock = MockProvider("OpenAI")
    gemini_mock = MockProvider("Gemini")
    claude_mock = MockProvider("Claude")

    gateway.register_provider(openai_mock)
    gateway.register_provider(gemini_mock)
    gateway.register_provider(claude_mock)

    assert len(gateway.get_configured_providers()) == 3

    # Admin selects Claude
    gateway.set_active_provider("Claude")
    assert gateway.active_provider_name == "Claude"
    resp = await gateway.generate([LLMMessage(role="user", content="Write content")])
    assert resp.provider == "Claude"
    assert len(claude_mock.call_history) == 1
    assert len(openai_mock.call_history) == 0
    assert len(gemini_mock.call_history) == 0

    # Admin switches to Gemini
    gateway.set_active_provider("Gemini")
    assert gateway.active_provider_name == "Gemini"
    resp2 = await gateway.generate([LLMMessage(role="user", content="SEO optimize")])
    assert resp2.provider == "Gemini"
    assert len(gemini_mock.call_history) == 1
    assert len(claude_mock.call_history) == 1


@pytest.mark.asyncio
async def test_matrix_test_5_no_providers_configured():
    """Test 5: No providers configured -> Application does NOT crash, raises clean error."""
    gateway = LLMGateway()
    gateway._providers.clear()
    gateway._active_provider_name = None

    assert gateway.is_operational() is False
    assert gateway.active_provider_name is None
    assert len(gateway.get_configured_providers()) == 0

    # Inspect safe metadata
    meta = gateway.get_provider_metadata()
    assert len(meta) == 4
    for m in meta:
        assert m["connection_status"] == "NOT_CONFIGURED"
        assert m["is_active"] is False

    # Calling AI generation produces NoProviderConfiguredError
    with pytest.raises(NoProviderConfiguredError) as exc_info:
        await gateway.generate([LLMMessage(role="user", content="Should fail gracefully")])

    assert exc_info.value.code == "AI_PROVIDER_REQUIRED"
    assert "No AI provider configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_fallback_behavior_disabled_by_default():
    """Requirement 8: Fallback should NOT occur unless explicitly enabled."""
    gateway = LLMGateway()
    gateway._providers.clear()
    gateway._fallback_enabled = False

    failing_openai = MockProvider("OpenAI", should_fail=True)
    working_gemini = MockProvider("Gemini", should_fail=False)

    gateway.register_provider(failing_openai, make_active=True)
    gateway.register_provider(working_gemini)

    # With fallback disabled, OpenAI failure raises error directly without silently calling Gemini
    with pytest.raises(ProviderUnavailableError):
        await gateway.generate([LLMMessage(role="user", content="Hello")])

    assert len(working_gemini.call_history) == 0
