export type ReviewStatus = 'pending' | 'reviewed' | 'failed'

export interface PullRequestSummary {
  id: string
  repository_full_name: string
  pr_number: number
  title: string
  author_login: string | null
  head_ref: string
  review_status: ReviewStatus
  ai_comments_count: number
  html_url: string | null
  created_at: string
  review_completed_at: string | null
}

export interface PullRequestListResponse {
  items: PullRequestSummary[]
  total: number
}

export interface ReviewRules {
  focus_security: boolean
  focus_performance: boolean
  focus_strict_typing: boolean
  focus_logic: boolean
  updated_at: string | null
}

export interface IssueTypeAnalyticsItem {
  issue_type: string
  label: string
  count: number
}

export interface IssueTypeAnalyticsResponse {
  days: number
  items: IssueTypeAnalyticsItem[]
}
