import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatINR(amount: number | undefined | null): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatDate(iso: string | undefined | null): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function confidenceLabel(score: number | undefined | null): string {
  if (score == null) return '—'
  if (score >= 0.85) return 'High'
  if (score >= 0.6) return 'Medium'
  return 'Low'
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    detected: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    prefilled: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    submitted: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    draft: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
    approved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    rejected: 'bg-red-500/15 text-red-300 border-red-500/30',
    under_review: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  }
  return map[status] || map.draft
}
