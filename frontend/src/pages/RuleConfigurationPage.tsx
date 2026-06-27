import { useEffect, useState, type ReactNode } from 'react'
import { Check, Loader2, Shield, Gauge, Braces, Bug } from 'lucide-react'

import { LoadingState } from '../components/LoadingState'
import { fetchReviewRules, isApiResponseValidationError, updateReviewRules } from '../lib/api'
import type { ReviewRules } from '../types/dashboard'

type SaveState = 'idle' | 'saving' | 'saved' | 'error'
const API_RESPONSE_FORMAT_MESSAGE = 'API response format changed — please refresh'

interface RuleToggleProps {
  id: keyof Omit<ReviewRules, 'updated_at'>
  label: string
  description: string
  icon: ReactNode
  checked: boolean
  onChange: (checked: boolean) => void
}

function RuleToggle({ id, label, description, icon, checked, onChange }: RuleToggleProps) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4 transition hover:border-slate-700"
    >
      <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-violet-400">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="font-medium text-slate-200">{label}</span>
          <input
            id={id}
            type="checkbox"
            checked={checked}
            onChange={(event) => onChange(event.target.checked)}
            className="h-5 w-5 rounded border-slate-600 bg-slate-800 text-violet-600 focus:ring-violet-500 focus:ring-offset-slate-900"
          />
        </div>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
    </label>
  )
}

export function RuleConfigurationPage() {
  const [rules, setRules] = useState<ReviewRules | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setLoadError(null)
      try {
        const data = await fetchReviewRules()
        if (!cancelled) setRules(data)
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            isApiResponseValidationError(error)
              ? API_RESPONSE_FORMAT_MESSAGE
              : error instanceof Error
                ? error.message
                : 'Failed to load rules',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  function updateRule<K extends keyof Omit<ReviewRules, 'updated_at'>>(key: K, value: boolean) {
    setRules((prev) => (prev ? { ...prev, [key]: value } : prev))
    setSaveState('idle')
  }

  async function handleSave() {
    if (!rules) return

    setSaveState('saving')
    setSaveError(null)
    try {
      const updated = await updateReviewRules({
        focus_security: rules.focus_security,
        focus_performance: rules.focus_performance,
        focus_strict_typing: rules.focus_strict_typing,
        focus_logic: rules.focus_logic,
      })
      setRules(updated)
      setSaveState('saved')
      setTimeout(() => setSaveState('idle'), 2000)
    } catch (error) {
      setSaveState('error')
      setSaveError(
        isApiResponseValidationError(error)
          ? API_RESPONSE_FORMAT_MESSAGE
          : error instanceof Error
            ? error.message
            : 'Failed to save rules',
      )
    }
  }

  if (loading) {
    return <LoadingState label="Loading rule configuration…" />
  }

  if (loadError || !rules) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
        {loadError ?? 'Unable to load configuration'}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-white">Rule Configuration</h2>
        <p className="mt-1 text-sm text-slate-400">
          Choose which issue categories the AI reviewer should surface on pull requests
        </p>
      </div>

      <div className="space-y-3">
        <RuleToggle
          id="focus_security"
          label="Security"
          description="Injection flaws, auth gaps, secret exposure, and unsafe deserialization"
          icon={<Shield className="h-5 w-5" />}
          checked={rules.focus_security}
          onChange={(v) => updateRule('focus_security', v)}
        />
        <RuleToggle
          id="focus_performance"
          label="Performance"
          description="N+1 queries, blocking I/O, and unnecessary allocations in hot paths"
          icon={<Gauge className="h-5 w-5" />}
          checked={rules.focus_performance}
          onChange={(v) => updateRule('focus_performance', v)}
        />
        <RuleToggle
          id="focus_strict_typing"
          label="Strict Typing"
          description="Missing annotations, unsafe casts, and type consistency violations"
          icon={<Braces className="h-5 w-5" />}
          checked={rules.focus_strict_typing}
          onChange={(v) => updateRule('focus_strict_typing', v)}
        />
        <RuleToggle
          id="focus_logic"
          label="Logic & Correctness"
          description="Incorrect conditionals, race conditions, and off-by-one errors"
          icon={<Bug className="h-5 w-5" />}
          checked={rules.focus_logic}
          onChange={(v) => updateRule('focus_logic', v)}
        />
      </div>

      {saveError ? <p className="text-sm text-rose-300">{saveError}</p> : null}

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saveState === 'saving'}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-60"
        >
          {saveState === 'saving' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : saveState === 'saved' ? (
            <Check className="h-4 w-4" />
          ) : null}
          {saveState === 'saving'
            ? 'Saving…'
            : saveState === 'saved'
              ? 'Saved'
              : 'Save preferences'}
        </button>
        {rules.updated_at ? (
          <p className="text-xs text-slate-500">
            Last updated {new Date(rules.updated_at).toLocaleString()}
          </p>
        ) : null}
      </div>
    </div>
  )
}
