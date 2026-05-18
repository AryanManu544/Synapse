-- Run once in Supabase → SQL Editor (uses direct connection, not the pooler).
-- Required because transaction pooler (port 6543) cannot reliably run DDL.

CREATE TABLE IF NOT EXISTS pull_requests (
    id UUID PRIMARY KEY,
    delivery_id VARCHAR(64),
    event_type VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    github_pr_id INTEGER NOT NULL,
    pr_number INTEGER NOT NULL,
    repository_full_name VARCHAR(255) NOT NULL,
    installation_id INTEGER,
    title VARCHAR(512) NOT NULL,
    author_login VARCHAR(255),
    head_sha VARCHAR(64) NOT NULL,
    base_sha VARCHAR(64) NOT NULL,
    head_ref VARCHAR(255) NOT NULL,
    base_ref VARCHAR(255) NOT NULL,
    html_url VARCHAR(512),
    diff_content TEXT,
    diff_fetched_at TIMESTAMPTZ,
    review_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    ai_comments_count INTEGER NOT NULL DEFAULT 0,
    review_error TEXT,
    review_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pull_requests_repo_number_head UNIQUE (repository_full_name, pr_number, head_sha)
);

CREATE INDEX IF NOT EXISTS ix_pull_requests_delivery_id ON pull_requests (delivery_id);
CREATE INDEX IF NOT EXISTS ix_pull_requests_github_pr_id ON pull_requests (github_pr_id);
CREATE INDEX IF NOT EXISTS ix_pull_requests_repository_full_name ON pull_requests (repository_full_name);
CREATE INDEX IF NOT EXISTS ix_pull_requests_review_status ON pull_requests (review_status);

CREATE TABLE IF NOT EXISTS review_rule_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    focus_security BOOLEAN NOT NULL DEFAULT TRUE,
    focus_performance BOOLEAN NOT NULL DEFAULT TRUE,
    focus_strict_typing BOOLEAN NOT NULL DEFAULT TRUE,
    focus_logic BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO review_rule_config (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS review_findings (
    id UUID PRIMARY KEY,
    pull_request_id UUID NOT NULL REFERENCES pull_requests (id) ON DELETE CASCADE,
    issue_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    line_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_review_findings_pull_request_id ON review_findings (pull_request_id);
CREATE INDEX IF NOT EXISTS ix_review_findings_issue_type ON review_findings (issue_type);
CREATE INDEX IF NOT EXISTS ix_review_findings_created_at ON review_findings (created_at);

ALTER TABLE pull_requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE review_rule_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE review_findings DISABLE ROW LEVEL SECURITY;
