import { ZodError, type ZodSchema } from 'zod'

import { HealthResponseSchema, type HealthResponse } from '../types/api'
import {
  IssueTypeAnalyticsResponseSchema,
  PullRequestListResponseSchema,
  ReviewRulesSchema,
  type IssueTypeAnalyticsResponse,
  type PullRequestListResponse,
  type ReviewRules,
} from '../types/dashboard'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiResponseValidationError extends Error {
  readonly fieldPath: string
  readonly zodError: ZodError

  constructor(error: ZodError) {
    const issue = error.issues[0]
    const fieldPath = issue?.path.length ? issue.path.join('.') : '(root)'
    const detail = issue?.message ?? 'Invalid response shape'
    super(`API response validation failed at ${fieldPath}: ${detail}`)
    this.name = 'ApiResponseValidationError'
    this.fieldPath = fieldPath
    this.zodError = error
  }
}

export function isApiResponseValidationError(error: unknown): error is ApiResponseValidationError {
  return error instanceof ApiResponseValidationError
}

async function request<T>(path: string, schema: ZodSchema<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new Error(
      `API returned non-JSON (status ${response.status}). Set VITE_API_BASE_URL to your Render API URL in Vercel and redeploy.`,
    )
  }

  const json: unknown = await response.json()
  try {
    return schema.parse(json)
  } catch (error) {
    if (error instanceof ZodError) {
      throw new ApiResponseValidationError(error)
    }
    throw error
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request('/api/v1/health', HealthResponseSchema)
}

export async function fetchPullRequests(): Promise<PullRequestListResponse> {
  return request('/api/v1/dashboard/pull-requests', PullRequestListResponseSchema)
}

export async function fetchReviewRules(): Promise<ReviewRules> {
  return request('/api/v1/dashboard/rules', ReviewRulesSchema)
}

export async function updateReviewRules(
  rules: Omit<ReviewRules, 'updated_at'>,
): Promise<ReviewRules> {
  return request('/api/v1/dashboard/rules', ReviewRulesSchema, {
    method: 'PUT',
    body: JSON.stringify(rules),
  })
}

export async function fetchIssueTypeAnalytics(days = 30): Promise<IssueTypeAnalyticsResponse> {
  return request(
    `/api/v1/dashboard/analytics/issue-types?days=${days}`,
    IssueTypeAnalyticsResponseSchema,
  )
}
