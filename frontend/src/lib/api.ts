import type {
  IssueTypeAnalyticsResponse,
  PullRequestListResponse,
  ReviewRules,
} from '../types/dashboard'
import type { HealthResponse } from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

  return response.json() as Promise<T>
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health')
}

export async function fetchPullRequests(): Promise<PullRequestListResponse> {
  return request<PullRequestListResponse>('/api/v1/dashboard/pull-requests')
}

export async function fetchReviewRules(): Promise<ReviewRules> {
  return request<ReviewRules>('/api/v1/dashboard/rules')
}

export async function updateReviewRules(
  rules: Omit<ReviewRules, 'updated_at'>,
): Promise<ReviewRules> {
  return request<ReviewRules>('/api/v1/dashboard/rules', {
    method: 'PUT',
    body: JSON.stringify(rules),
  })
}

export async function fetchIssueTypeAnalytics(days = 30): Promise<IssueTypeAnalyticsResponse> {
  return request<IssueTypeAnalyticsResponse>(`/api/v1/dashboard/analytics/issue-types?days=${days}`)
}
