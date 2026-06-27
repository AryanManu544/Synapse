import { z } from 'zod'

export const ReviewStatusSchema = z.enum(['pending', 'reviewed', 'failed'])
export type ReviewStatus = z.infer<typeof ReviewStatusSchema>

export const PullRequestSummarySchema = z.object({
  id: z.string().uuid(),
  repository_full_name: z.string(),
  pr_number: z.number().int().positive(),
  title: z.string(),
  author_login: z.string().nullable(),
  head_ref: z.string(),
  review_status: ReviewStatusSchema,
  ai_comments_count: z.number().int().nonnegative(),
  html_url: z.string().url().nullable(),
  created_at: z.string().datetime({ offset: true }),
  review_completed_at: z.string().datetime({ offset: true }).nullable(),
})
export type PullRequestSummary = z.infer<typeof PullRequestSummarySchema>

export const PullRequestListResponseSchema = z.object({
  items: z.array(PullRequestSummarySchema),
  total: z.number().int().nonnegative(),
})
export type PullRequestListResponse = z.infer<typeof PullRequestListResponseSchema>

export const ReviewRulesSchema = z.object({
  focus_security: z.boolean(),
  focus_performance: z.boolean(),
  focus_strict_typing: z.boolean(),
  focus_logic: z.boolean(),
  updated_at: z.string().datetime({ offset: true }).nullable(),
})
export type ReviewRules = z.infer<typeof ReviewRulesSchema>

export const IssueTypeAnalyticsItemSchema = z.object({
  issue_type: z.string(),
  label: z.string(),
  count: z.number().int().nonnegative(),
})
export type IssueTypeAnalyticsItem = z.infer<typeof IssueTypeAnalyticsItemSchema>

export const IssueTypeAnalyticsResponseSchema = z.object({
  days: z.number().int().positive(),
  items: z.array(IssueTypeAnalyticsItemSchema),
})
export type IssueTypeAnalyticsResponse = z.infer<typeof IssueTypeAnalyticsResponseSchema>
