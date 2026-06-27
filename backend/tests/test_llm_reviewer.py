import pytest
from pydantic import ValidationError

from app.models.schemas.code_review import CodeReviewResult, ReviewComment, ReviewSeverity
from app.services.llm_reviewer import (
    LLMMalformedResponseError,
    _parse_fallback_json,
    filter_diff_noise,
    truncate_diff,
)

SAMPLE_DIFF = """\
diff --git a/package-lock.json b/package-lock.json
index 111..222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,2 +1,2 @@
-  "old": true
+  "new": true
diff --git a/src/app.py b/src/app.py
index 333..444 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,4 @@
 context line
-removed bug
+added feature
diff --git a/assets/logo.svg b/assets/logo.svg
index 555..666 100644
--- a/assets/logo.svg
+++ b/assets/logo.svg
@@ -1 +1 @@
-<svg></svg>
+<svg><title>x</title></svg>
"""


def test_filter_diff_noise_excludes_lockfiles_and_svg() -> None:
    filtered = filter_diff_noise(SAMPLE_DIFF)

    assert "package-lock.json" not in filtered
    assert "logo.svg" not in filtered
    assert "src/app.py" in filtered


def test_filter_diff_noise_strips_deleted_lines() -> None:
    filtered = filter_diff_noise(SAMPLE_DIFF)

    assert "-removed bug" not in filtered
    assert "+added feature" in filtered
    assert " context line" in filtered or "context line" in filtered


def test_filter_diff_noise_empty_input() -> None:
    assert filter_diff_noise("") == ""
    assert filter_diff_noise("   \n") == ""


def test_truncate_diff_respects_file_boundaries() -> None:
    large = SAMPLE_DIFF * 50
    truncated = truncate_diff(large, max_chars=800)

    assert len(truncated) <= 800
    assert "diff --git" in truncated


def test_parse_fallback_json_valid() -> None:
    raw = (
        '{"comments": [{"file_path": "a.py", "line_number": 1, "severity": "High", '
        '"issue_type": "security", "suggested_fix": "fix"}]}'
    )
    result = _parse_fallback_json(raw)

    assert len(result.comments) == 1
    assert result.comments[0].severity == ReviewSeverity.HIGH


def test_parse_fallback_json_strips_markdown_fence() -> None:
    raw = """```json
{
  "comments": [{
    "file_path": "a.py",
    "line_number": 2,
    "severity": "Low",
    "issue_type": "logic",
    "suggested_fix": "nit"
  }]
}
```"""
    result = _parse_fallback_json(raw)
    assert result.comments[0].line_number == 2


def test_parse_fallback_json_invalid_raises() -> None:
    with pytest.raises(LLMMalformedResponseError):
        _parse_fallback_json("not json")


def test_code_review_result_schema() -> None:
    result = CodeReviewResult(
        comments=[
            ReviewComment(
                file_path="src/main.py",
                line_number=10,
                severity=ReviewSeverity.MEDIUM,
                issue_type="security",
                suggested_fix="Use parameterized queries.",
            )
        ]
    )
    assert result.comments[0].severity.value == "Medium"


def test_code_review_result_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        CodeReviewResult.model_validate(
            {
                "comments": [
                    {
                        "file_path": "a.py",
                        "line_number": 1,
                        "severity": "Critical",
                        "issue_type": "security",
                        "suggested_fix": "x",
                    }
                ]
            }
        )
