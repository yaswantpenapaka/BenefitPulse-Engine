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

/** True when agents found claim-eligible card protection. */
export function isClaimEligible(status?: string | null, benefitType?: string | null): boolean {
  const s = (status || '').toLowerCase()
  const t = (benefitType || '').toLowerCase()
  if (['not_eligible', 'ineligible', 'declined'].includes(s)) return false
  if (['outside coverage', 'no protection match', 'not covered'].includes(t)) return false
  return ['detected', 'prefilled', 'submitted', 'approved', 'under_review'].includes(s)
}

/** Finance-facing labels for detection status. */
export function coverageStatusLabel(status?: string | null, benefitType?: string | null): string {
  if (!isClaimEligible(status, benefitType)) return 'Outside coverage'
  const s = (status || '').toLowerCase()
  if (s === 'prefilled') return 'Claim ready'
  if (s === 'submitted') return 'Claim filed'
  if (s === 'approved') return 'Claim approved'
  if (s === 'under_review') return 'Under review'
  return 'Coverage available'
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    detected: 'bg-teal-100 text-teal-900 border-teal-300',
    prefilled: 'bg-amber-100 text-amber-950 border-amber-300',
    submitted: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    draft: 'bg-stone-100 text-stone-700 border-stone-300',
    approved: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    rejected: 'bg-orange-100 text-orange-900 border-orange-300',
    under_review: 'bg-violet-100 text-violet-900 border-violet-300',
    not_eligible: 'bg-stone-200 text-stone-800 border-stone-400',
    ineligible: 'bg-stone-200 text-stone-800 border-stone-400',
    declined: 'bg-stone-200 text-stone-800 border-stone-400',
  }
  return map[status] || map.draft
}

/** Map card product names/types to multi-color card face styles. */
export function cardFaceClass(cardType?: string | null, cardName?: string | null): string {
  const hay = `${cardType || ''} ${cardName || ''}`.toLowerCase()
  if (hay.includes('gold')) return 'amex-card-gold'
  if (hay.includes('green')) return 'amex-card-green'
  if (hay.includes('blue cash') || hay.includes('bluecash')) return 'amex-card-blue-cash'
  if (hay.includes('centurion') || hay.includes('black')) return 'amex-card-platinum'
  return 'amex-card-platinum'
}
