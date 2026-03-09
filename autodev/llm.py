"""LLM abstraction layer supporting both Claude Code CLI and Anthropic API."""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    success: bool
    error: str | None = None


def get_llm_backend() -> str:
    """Determine which LLM backend to use.

    Returns 'api' if ANTHROPIC_API_KEY is set, otherwise 'cli'.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api"
    return "cli"


def query_llm(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    model: str = "claude-sonnet-4-20250514",
) -> LLMResponse:
    """Query LLM using either Claude Code CLI or Anthropic API.

    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens in response
        model: Model to use (for API mode)

    Returns:
        LLMResponse with content or error
    """
    backend = get_llm_backend()

    if backend == "api":
        return _query_api(prompt, system_prompt, max_tokens, model)
    else:
        return _query_cli(prompt, system_prompt)


def _query_api(
    prompt: str,
    system_prompt: str | None,
    max_tokens: int,
    model: str,
) -> LLMResponse:
    """Query using Anthropic API."""
    try:
        from anthropic import Anthropic

        client = Anthropic()

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)
        content = response.content[0].text

        return LLMResponse(content=content, success=True)

    except Exception as e:
        logger.error(f"API query failed: {e}")
        return LLMResponse(content="", success=False, error=str(e))


def _query_cli(
    prompt: str,
    system_prompt: str | None,
) -> LLMResponse:
    """Query using Claude Code CLI.

    Uses `claude` CLI with --print flag for non-interactive output.
    """
    try:
        # Build the full prompt with system context
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"""<system>
{system_prompt}
</system>

{prompt}"""

        # Run claude CLI with --print for non-interactive mode
        # Using --output-format text for plain text output
        result = subprocess.run(
            [
                "claude",
                "--print",  # Non-interactive, just print response
                "--output-format", "text",  # Plain text output
                "--dangerously-skip-permissions",  # Skip permission prompts for automation
            ],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.getcwd(),
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return LLMResponse(
                content="",
                success=False,
                error=f"CLI failed (exit {result.returncode}): {error_msg}",
            )

        output = result.stdout.strip()
        if not output:
            return LLMResponse(
                content="",
                success=False,
                error="CLI returned empty response",
            )

        return LLMResponse(content=output, success=True)

    except FileNotFoundError:
        return LLMResponse(
            content="",
            success=False,
            error="Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
        )
    except subprocess.TimeoutExpired:
        return LLMResponse(
            content="",
            success=False,
            error="CLI query timed out after 5 minutes",
        )
    except Exception as e:
        logger.error(f"CLI query failed: {e}")
        return LLMResponse(content="", success=False, error=str(e))


def extract_json(content: str) -> dict | list | None:
    """Extract JSON from LLM response.

    Handles responses with markdown code blocks.
    """
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting from code blocks
    if "```json" in content:
        try:
            json_str = content.split("```json")[1].split("```")[0]
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    if "```" in content:
        try:
            json_str = content.split("```")[1].split("```")[0]
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    # Try finding JSON object/array in content
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = content.find(start_char)
        if start != -1:
            # Find matching end
            depth = 0
            for i, char in enumerate(content[start:], start):
                if char == start_char:
                    depth += 1
                elif char == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(content[start:i+1])
                        except json.JSONDecodeError:
                            break

    return None
