import { NavLink, Outlet } from 'react-router-dom'
import { BarChart3, Bot, GitPullRequest, Settings2 } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/pull-requests', label: 'Pull Requests', icon: GitPullRequest },
  { to: '/rules', label: 'Rule Configuration', icon: Settings2 },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
] as const

export function DashboardLayout() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900/80">
        <div className="flex items-center gap-2 border-b border-slate-800 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold tracking-tight">Synapse</p>
            <p className="text-xs text-slate-500">AI Code Review</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-violet-600/20 text-violet-200'
                    : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-200',
                ].join(' ')
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800 p-4 text-xs text-slate-500">
          Engineering Manager Dashboard
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-800 bg-slate-900/40 px-8 py-5 backdrop-blur">
          <h1 className="text-lg font-semibold text-slate-200">AI Reviewer Monitor</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Track pull request reviews, tune rules, and analyze findings
          </p>
        </header>
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
