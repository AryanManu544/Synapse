-- GitHub PR ids exceed 32-bit integer max (~2.1B). Run once in Supabase SQL Editor.
ALTER TABLE pull_requests
    ALTER COLUMN github_pr_id TYPE BIGINT;
