import { ExternalLink, RefreshCw } from 'lucide-react'

import { LoadingState } from '../components/LoadingState'
import { StatusBadge } from '../components/StatusBadge'
import { useAsync } from '../hooks/useAsync'
import { fetchPullRequests } from '../lib/api'
import type { PullRequestSummary } from '../types/dashboard'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso))
}

export function PullRequestsPage() {
  const { state, reload } = useAsync(() => fetchPullRequests())

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-white">Pull Requests</h2>
          <p className="mt-1 text-sm text-slate-400">Recent PRs processed by the AI reviewer</p>
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          disabled={state.status === 'loading'}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-600 hover:text-white disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${state.status === 'loading' ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {state.status === 'loading' || state.status === 'idle' ? (
        <LoadingState label="Loading pull requests…" />
      ) : null}

      {state.status === 'error' ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          Failed to load pull requests: {state.message}
        </div>
      ) : null}

      {state.status === 'success' ? (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Repository</th>
                  <th className="px-4 py-3 font-medium">PR</th>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Author</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">AI Comments</th>
                  <th className="px-4 py-3 font-medium">Updated</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {state.data.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      No pull requests yet. Webhook deliveries will appear here.
                    </td>
                  </tr>
                ) : (
                  state.data.items.map((pr: PullRequestSummary) => (
                    <tr key={pr.id} className="hover:bg-slate-800/30">
                      <td className="px-4 py-3 font-mono text-xs text-slate-400">
                        {pr.repository_full_name}
                      </td>
                      <td className="px-4 py-3 font-medium text-violet-300">#{pr.pr_number}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-slate-200" title={pr.title}>
                        {pr.title}
                      </td>
                      <td className="px-4 py-3 text-slate-400">{pr.author_login ?? '—'}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={pr.review_status} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">
                        {pr.ai_comments_count}
                      </td>
                      <td className="px-4 py-3 text-slate-500">
                        {formatDate(pr.review_completed_at ?? pr.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        {pr.html_url ? (
                          <a
                            href={pr.html_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex text-slate-400 hover:text-violet-300"
                            aria-label={`Open PR #${pr.pr_number} on GitHub`}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        ) : null}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {state.data.total > 0 ? (
            <div className="border-t border-slate-800 px-4 py-2 text-xs text-slate-500">
              Showing {state.data.items.length} of {state.data.total} pull requests
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
