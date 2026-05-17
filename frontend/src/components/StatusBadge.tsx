import type { ReviewStatus } from '../types/dashboard'

const STYLES: Record<ReviewStatus, string> = {
  pending: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  reviewed: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  failed: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
}

const LABELS: Record<ReviewStatus, string> = {
  pending: 'Pending',
  reviewed: 'Reviewed',
  failed: 'Failed',
}

interface StatusBadgeProps {
  status: ReviewStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  )
}
