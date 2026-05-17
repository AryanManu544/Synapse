import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { RefreshCw } from 'lucide-react'

import { LoadingState } from '../components/LoadingState'
import { useAsync } from '../hooks/useAsync'
import { fetchIssueTypeAnalytics } from '../lib/api'

const CHART_COLORS = ['#8b5cf6', '#6366f1', '#22d3ee', '#34d399', '#fbbf24']

export function AnalyticsPage() {
  const { state, reload } = useAsync(() => fetchIssueTypeAnalytics(30))

  const chartData =
    state.status === 'success' ? state.data.items.filter((item) => item.count > 0) : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-white">Analytics</h2>
          <p className="mt-1 text-sm text-slate-400">
            Most common AI-detected issue types over the last 30 days
          </p>
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
        <LoadingState label="Loading analytics…" />
      ) : null}

      {state.status === 'error' ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          Failed to load analytics: {state.message}
        </div>
      ) : null}

      {state.status === 'success' ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
          {chartData.length === 0 ? (
            <p className="py-16 text-center text-sm text-slate-500">
              No findings recorded in the last 30 days yet.
            </p>
          ) : (
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                    axisLine={{ stroke: '#475569' }}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(139, 92, 246, 0.08)' }}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '0.5rem',
                      color: '#e2e8f0',
                    }}
                  />
                  <Bar dataKey="count" name="Findings" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={entry.issue_type}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
