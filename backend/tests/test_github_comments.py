from app.models.schemas.code_review import CodeReviewResult, ReviewComment, ReviewSeverity
from app.services.github import (
    BOT_NAME,
    format_review_comment_body,
    format_review_summary_body,
)


def test_format_review_comment_body_includes_bot_and_severity() -> None:
    comment = ReviewComment(
        file_path="src/auth.py",
        line_number=42,
        severity=ReviewSeverity.HIGH,
        issue_type="security",
        suggested_fix="Use `secrets.compare_digest` for token comparison.",
    )
    body = format_review_comment_body(comment)

    assert BOT_NAME in body
    assert "🔴 High" in body
    assert "secrets.compare_digest" in body
    assert "🤖" in body


def test_format_review_summary_body_with_findings() -> None:
    result = CodeReviewResult(
        comments=[
            ReviewComment(
                file_path="a.py",
                line_number=1,
                severity=ReviewSeverity.HIGH,
                issue_type="security",
                suggested_fix="fix",
            ),
            ReviewComment(
                file_path="b.py",
                line_number=2,
                severity=ReviewSeverity.LOW,
                issue_type="typing",
                suggested_fix="nit",
            ),
        ]
    )
    body = format_review_summary_body(result)

    assert "Summary" in body
    assert "| 🔴 High | 1 |" in body
    assert "2** finding" in body
    assert "Findings (quick view)" in body
    assert "`a.py:1`" in body
    assert "`b.py:2`" in body


def test_format_review_summary_body_empty() -> None:
    body = format_review_summary_body(CodeReviewResult())
    assert "No security" in body
    assert BOT_NAME in body
