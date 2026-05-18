from __future__ import annotations

import json
import logging
import re
import time
from typing import Final

from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.core.config import Settings
from app.models.schemas.code_review import CodeReviewResult
from app.services.base import BaseService

logger = logging.getLogger(__name__)

DIFF_GIT_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)

EXCLUDED_BASENAMES: Final[frozenset[str]] = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }
)

EXCLUDED_SUFFIXES: Final[tuple[str, ...]] = (".svg",)

SYSTEM_PROMPT: Final[str] = """You are a strict Principal Software Engineer performing a production code review.

Your mandate:
- Identify security flaws (injection, authz/authn gaps, secret exposure, unsafe deserialization, etc.).
- Identify performance bottlenecks (N+1 queries, unnecessary allocations, blocking I/O in hot paths, etc.).
- Identify logical bugs (incorrect conditionals, race conditions, off-by-one errors, null/undefined mishandling).

Rules:
- Only comment on issues evidenced by the provided diff. Do not speculate about code you cannot see.
- Prefer fewer, high-signal comments over noisy nitpicks.
- Every comment MUST include a concrete suggested_fix (code snippet or precise steps).
- Use severity High for exploitable security issues or data-loss/corruption risks.
- Use severity Medium for likely bugs or meaningful performance regressions.
- Use severity Low for maintainability issues that could become bugs later.
- line_number MUST refer to the 1-based line number in the NEW file (after changes).
- issue_type MUST be one of: security, performance, typing, logic.
- Return ONLY valid JSON matching the required schema. No markdown fences or prose outside JSON.
"""

GROQ_JSON_SHAPE: Final[str] = """
Your entire reply MUST be one JSON object (no markdown code fences). Exact shape:
{
  "comments": [
    {
      "file_path": "path/in/repo.ext",
      "line_number": 42,
      "severity": "Low",
      "issue_type": "security",
      "suggested_fix": "Concrete fix text."
    }
  ]
}
Rules for JSON:
- "severity" must be exactly one of: "Low", "Medium", "High" (capital first letter).
- "issue_type" must be one of: "security", "performance", "typing", "logic".
- If there are no issues, return {"comments": []}.
"""


class LLMReviewerError(Exception):
    """Base error for LLM review failures."""


class LLMRateLimitError(LLMReviewerError):
    """Raised when the provider rate-limits requests after retries are exhausted."""


class LLMTokenLimitError(LLMReviewerError):
    """Raised when the diff cannot fit within model context even after truncation."""


class LLMMalformedResponseError(LLMReviewerError):
    """Raised when the model returns unparseable structured output after retries."""


def filter_diff_noise(raw_diff: str) -> str:
    """
    Remove low-signal diff content before LLM review.

    - Drops entire files matching lockfiles and binary-ish assets (e.g. .svg).
    - Strips deleted lines (``-`` hunks) so the model focuses on incoming changes.
    """
    if not raw_diff.strip():
        return ""

    filtered_hunks: list[str] = []
    for file_path, hunk in _iter_file_hunks(raw_diff):
        if _should_exclude_file(file_path):
            logger.debug("Excluded diff hunk for file: %s", file_path)
            continue
        stripped = _strip_deleted_lines(hunk)
        if stripped.strip():
            filtered_hunks.append(stripped)

    return "".join(filtered_hunks)


def _iter_file_hunks(raw_diff: str) -> list[tuple[str, str]]:
    """Split a unified diff into (file_path, hunk_text) pairs."""
    lines = raw_diff.splitlines(keepends=True)
    hunks: list[tuple[str, str]] = []
    current_path = ""
    buffer: list[str] = []

    for line in lines:
        if line.startswith("diff --git "):
            if buffer:
                hunks.append((current_path, "".join(buffer)))
            current_path = _parse_diff_git_path(line)
            buffer = [line]
        else:
            if not buffer and not current_path:
                continue
            buffer.append(line)

    if buffer:
        hunks.append((current_path, "".join(buffer)))

    return hunks


def _parse_diff_git_path(diff_git_line: str) -> str:
    match = DIFF_GIT_HEADER_RE.match(diff_git_line.strip())
    if match:
        return match.group(2)
    return diff_git_line.removeprefix("diff --git ").strip()


def _should_exclude_file(file_path: str) -> bool:
    normalized = file_path.strip().lstrip("./")
    basename = normalized.rsplit("/", 1)[-1]
    if basename in EXCLUDED_BASENAMES:
        return True
    return any(normalized.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def _strip_deleted_lines(hunk: str) -> str:
    """Remove ``-`` lines from a unified diff hunk (keep ``---`` file headers)."""
    kept: list[str] = []
    for line in hunk.splitlines(keepends=True):
        if line.startswith("-") and not line.startswith("---"):
            continue
        kept.append(line)
    return "".join(kept)


def truncate_diff(diff: str, max_chars: int) -> str:
    """Truncate diff at file boundaries to stay within token limits."""
    if len(diff) <= max_chars:
        return diff

    truncated: list[str] = []
    size = 0
    for _path, hunk in _iter_file_hunks(diff):
        if size + len(hunk) > max_chars:
            break
        truncated.append(hunk)
        size += len(hunk)

    if not truncated:
        return diff[:max_chars]

    result = "".join(truncated)
    logger.warning(
        "Diff truncated from %d to %d characters to respect token limits",
        len(diff),
        len(result),
    )
    return result


class LLMReviewer(BaseService):
    """Review pull request diffs via an LLM with structured JSON output."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._openai_client: OpenAI | None = None
        self._groq_client: OpenAI | None = None

    def _get_openai_client(self) -> OpenAI:
        if not self._settings.openai_api_key:
            raise LLMReviewerError("OPENAI_API_KEY is not configured.")
        if self._openai_client is None:
            self._openai_client = OpenAI(
                api_key=self._settings.openai_api_key,
                max_retries=0,
            )
        return self._openai_client

    def _get_groq_client(self) -> OpenAI:
        if not self._settings.groq_api_key:
            raise LLMReviewerError("GROQ_API_KEY is not configured.")
        if self._groq_client is None:
            base = self._settings.groq_api_base.rstrip("/")
            self._groq_client = OpenAI(
                api_key=self._settings.groq_api_key,
                base_url=base,
                max_retries=0,
            )
        return self._groq_client

    def review_diff(self, raw_diff: str) -> CodeReviewResult:
        """
        Filter diff noise, send to the LLM, and return structured review comments.

        Retries on rate limits, token overflows (with truncation), and malformed JSON.
        """
        filtered = filter_diff_noise(raw_diff)
        if not filtered.strip():
            logger.info("No reviewable diff content after filtering")
            return CodeReviewResult(comments=[])

        return self._review_with_retry(filtered)

    def _review_with_retry(self, diff: str) -> CodeReviewResult:
        max_retries = self._settings.llm_max_retries
        delay = self._settings.llm_retry_base_delay_seconds
        working_diff = truncate_diff(diff, self._settings.llm_max_diff_chars)
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return self._invoke_structured_review(working_diff, repair_mode=False)
            except RateLimitError as exc:
                last_error = exc
                sleep_for = delay * (2 ** (attempt - 1))
                logger.warning(
                    "LLM rate limit (attempt %d/%d); sleeping %.1fs",
                    attempt,
                    max_retries,
                    sleep_for,
                )
                if attempt == max_retries:
                    raise LLMRateLimitError("LLM rate limit exceeded after retries") from exc
                time.sleep(sleep_for)
            except APIError as exc:
                if _is_token_limit_error(exc):
                    last_error = exc
                    working_diff = truncate_diff(
                        working_diff,
                        max(int(len(working_diff) * 0.7), 4_000),
                    )
                    logger.warning(
                        "Token/context limit hit (attempt %d/%d); truncated diff to %d chars",
                        attempt,
                        max_retries,
                        len(working_diff),
                    )
                    if len(working_diff) < 500:
                        raise LLMTokenLimitError(
                            "Diff too large for model context even after truncation"
                        ) from exc
                    continue

                raise LLMReviewerError(f"LLM API error: {exc}") from exc
            except (LLMMalformedResponseError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Malformed LLM response (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt == max_retries:
                    break
                try:
                    return self._invoke_structured_review(working_diff, repair_mode=True)
                except (LLMMalformedResponseError, ValidationError, RateLimitError, APIError):
                    delay_sleep = delay * (2 ** (attempt - 1))
                    time.sleep(delay_sleep)
            except APITimeoutError as exc:
                last_error = exc
                logger.warning("LLM timeout (attempt %d/%d)", attempt, max_retries)
                if attempt == max_retries:
                    raise LLMReviewerError("LLM request timed out after retries") from exc
                time.sleep(delay * (2 ** (attempt - 1)))

        raise LLMMalformedResponseError(
            "Failed to obtain valid structured LLM response after retries"
        ) from last_error

    def _invoke_structured_review(self, diff: str, *, repair_mode: bool) -> CodeReviewResult:
        if self._settings.llm_default_provider == "groq":
            return self._invoke_groq_json(diff, repair_mode=repair_mode)
        if self._settings.llm_default_provider == "anthropic":
            raise LLMReviewerError("Anthropic is not implemented; use openai or groq.")
        return self._invoke_openai_parse(diff, repair_mode=repair_mode)

    def _invoke_openai_parse(self, diff: str, *, repair_mode: bool) -> CodeReviewResult:
        client = self._get_openai_client()
        user_content = _build_user_prompt(diff, repair_mode=repair_mode)

        try:
            completion = client.beta.chat.completions.parse(
                model=self._settings.llm_default_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=CodeReviewResult,
                temperature=0.2,
            )
        except RateLimitError:
            raise
        except APIError as exc:
            if _is_token_limit_error(exc):
                raise
            raise LLMReviewerError(f"OpenAI API error: {exc}") from exc

        message = completion.choices[0].message
        if message.parsed is not None:
            return message.parsed

        raw = message.content
        if raw:
            return _parse_fallback_json(raw)

        raise LLMMalformedResponseError("Model returned empty content")

    def _invoke_groq_json(self, diff: str, *, repair_mode: bool) -> CodeReviewResult:
        client = self._get_groq_client()
        user_content = _build_user_prompt(diff, repair_mode=repair_mode)
        system = SYSTEM_PROMPT + GROQ_JSON_SHAPE

        try:
            completion = client.chat.completions.create(
                model=self._settings.llm_default_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except RateLimitError:
            raise
        except APIError as exc:
            if _is_token_limit_error(exc):
                raise
            raise LLMReviewerError(f"Groq API error: {exc}") from exc

        raw = completion.choices[0].message.content
        if not raw:
            raise LLMMalformedResponseError("Groq returned empty content")
        return _parse_fallback_json(raw)

    def review_diff_from_raw(self, raw_diff: str) -> CodeReviewResult:
        """Alias for ``review_diff`` — filters and reviews in one call."""
        return self.review_diff(raw_diff)


def _build_user_prompt(diff: str, *, repair_mode: bool) -> str:
    if repair_mode:
        return (
            "Your previous response was malformed or did not match the required JSON schema. "
            "Review the diff again and respond with ONLY valid JSON.\n\n"
            f"```diff\n{diff}\n```"
        )
    return (
        "Review the following pull request diff. Return structured JSON with a `comments` array.\n\n"
        f"```diff\n{diff}\n```"
    )


def _parse_fallback_json(raw: str) -> CodeReviewResult:
    """Best-effort parse when structured output parsing fails but text is present."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMMalformedResponseError("Response is not valid JSON") from exc

    try:
        return CodeReviewResult.model_validate(payload)
    except ValidationError as exc:
        raise LLMMalformedResponseError("JSON does not match CodeReviewResult schema") from exc


def _is_token_limit_error(exc: APIError) -> bool:
    message = str(exc).lower()
    tokens = ("token", "context length", "maximum context", "too large", "context_window")
    return any(token in message for token in tokens)
