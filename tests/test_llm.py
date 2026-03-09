"""Tests for LLM abstraction layer."""

import os
from unittest.mock import MagicMock, patch

import pytest

from autodev.llm import (
    LLMResponse,
    extract_json,
    get_llm_backend,
    query_llm,
)


class TestGetLLMBackend:
    """Tests for backend selection."""

    def test_returns_api_when_key_set(self):
        """Should return 'api' when ANTHROPIC_API_KEY is set."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            assert get_llm_backend() == "api"

    def test_returns_cli_when_no_key(self):
        """Should return 'cli' when no API key."""
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            assert get_llm_backend() == "cli"


class TestExtractJson:
    """Tests for JSON extraction."""

    def test_extracts_direct_json(self):
        """Should parse direct JSON."""
        content = '{"key": "value"}'
        result = extract_json(content)
        assert result == {"key": "value"}

    def test_extracts_from_markdown_code_block(self):
        """Should extract JSON from markdown code block."""
        content = '''Here is the analysis:

```json
{"summary": "test", "opportunities": []}
```

That's it.'''
        result = extract_json(content)
        assert result == {"summary": "test", "opportunities": []}

    def test_extracts_from_generic_code_block(self):
        """Should extract JSON from generic code block."""
        content = '''Result:

```
{"key": "value"}
```'''
        result = extract_json(content)
        assert result == {"key": "value"}

    def test_extracts_embedded_json_object(self):
        """Should find JSON object in text."""
        content = 'The result is {"found": true} in the response.'
        result = extract_json(content)
        assert result == {"found": True}

    def test_extracts_json_array(self):
        """Should extract JSON array."""
        content = '[1, 2, 3]'
        result = extract_json(content)
        assert result == [1, 2, 3]

    def test_returns_none_for_invalid_json(self):
        """Should return None for invalid JSON."""
        content = "This is not JSON at all"
        result = extract_json(content)
        assert result is None

    def test_handles_nested_json(self):
        """Should handle nested JSON structures."""
        content = '''```json
{
    "summary": "Analysis complete",
    "opportunities": [
        {
            "title": "Add feature",
            "priority": 1
        }
    ]
}
```'''
        result = extract_json(content)
        assert result["summary"] == "Analysis complete"
        assert len(result["opportunities"]) == 1


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_success_response(self):
        """Should create success response."""
        response = LLMResponse(content="test", success=True)
        assert response.content == "test"
        assert response.success is True
        assert response.error is None

    def test_error_response(self):
        """Should create error response."""
        response = LLMResponse(content="", success=False, error="Failed")
        assert response.content == ""
        assert response.success is False
        assert response.error == "Failed"


class TestQueryLLM:
    """Tests for query_llm function."""

    @patch("autodev.llm.get_llm_backend")
    @patch("autodev.llm._query_api")
    def test_uses_api_backend(self, mock_query_api, mock_backend):
        """Should use API when backend is 'api'."""
        mock_backend.return_value = "api"
        mock_query_api.return_value = LLMResponse(content="response", success=True)

        result = query_llm("test prompt")

        mock_query_api.assert_called_once()
        assert result.success is True

    @patch("autodev.llm.get_llm_backend")
    @patch("autodev.llm._query_cli")
    def test_uses_cli_backend(self, mock_query_cli, mock_backend):
        """Should use CLI when backend is 'cli'."""
        mock_backend.return_value = "cli"
        mock_query_cli.return_value = LLMResponse(content="response", success=True)

        result = query_llm("test prompt")

        mock_query_cli.assert_called_once()
        assert result.success is True

    @patch("autodev.llm.get_llm_backend")
    @patch("autodev.llm._query_api")
    def test_passes_system_prompt_to_api(self, mock_query_api, mock_backend):
        """Should pass system prompt to API backend."""
        mock_backend.return_value = "api"
        mock_query_api.return_value = LLMResponse(content="response", success=True)

        query_llm("test prompt", system_prompt="You are helpful")

        args, kwargs = mock_query_api.call_args
        assert args[1] == "You are helpful"
