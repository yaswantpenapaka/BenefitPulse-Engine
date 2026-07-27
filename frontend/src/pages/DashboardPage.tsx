import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CircleSlash2,
  CreditCard,
  IndianRupee,
  ListOrdered,
  ShieldCheck,
  ShieldOff,
  Wallet,
  Zap,
} from 'lucide-react'
import { api } from '@/lib/api'
import {
  confidenceLabel,
  cn,
  formatDate,
  formatINR,
  statusColor,
  cardFaceClass,
  isClaimEligible,
  coverageStatusLabel,
} from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.dashboard(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        Loading your benefits…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-destructive">
        Failed to load dashboard: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  const { profile, cards, detected_benefits, stats } = data
  const claimEligibleCount =
    stats.claim_eligible ??
    detected_benefits.filter((b) => isClaimEligible(b.status, b.benefit_type)).length
  const outsideCount =
    stats.outside_coverage ??
    detected_benefits.filter((b) => !isClaimEligible(b.status, b.benefit_type)).length

  // Recent mix: prefer both outcomes in the first strip
  const eligibleRecent = detected_benefits.filter((b) =>
    isClaimEligible(b.status, b.benefit_type),
  )
  const outsideRecent = detected_benefits.filter(
    (b) => !isClaimEligible(b.status, b.benefit_type),
  )
  const topBenefits = [
    ...eligibleRecent.slice(0, 2),
    ...outsideRecent.slice(0, 1),
    ...eligibleRecent.slice(2),
    ...outsideRecent.slice(1),
  ].slice(0, 4)

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 shadow-sm">
        <p className="text-sm text-primary font-semibold tracking-wide uppercase">
          Welcome back
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-3xl sm:text-4xl font-bold text-foreground">
          {profile?.full_name || 'Card Member'}
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Coverage review snapshot for your linked cards — claim-eligible charges and items
          outside policy, ready for action from the workspace bar.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: 'Claim-eligible',
            value: claimEligibleCount,
            icon: ShieldCheck,
            tone: 'bg-emerald-100 text-emerald-800',
          },
          {
            label: 'Outside coverage',
            value: outsideCount,
            icon: ShieldOff,
            tone: 'bg-stone-200 text-stone-800',
          },
          {
            label: 'Linked cards',
            value: stats.cards_count,
            icon: CreditCard,
            tone: 'bg-amber-100 text-amber-900',
          },
          {
            label: 'Potential cover',
            value: formatINR(stats.potential_coverage),
            icon: Wallet,
            tone: 'bg-primary/10 text-primary',
          },
        ].map((s) => (
          <Card key={s.label} className="border-border shadow-sm">
            <CardContent className="flex items-center gap-4 p-5">
              <div className={cn('rounded-xl p-3', s.tone)}>
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <div className="text-2xl font-semibold tracking-tight">{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          {
            to: '/benefits',
            label: 'Coverage ledger',
            hint: 'Eligible & outside coverage',
            icon: ShieldCheck,
            color: 'border-primary/30 hover:border-primary/60',
          },
          {
            to: '/transactions',
            label: 'Posted charges',
            hint: 'Run coverage assessment',
            icon: ListOrdered,
            color: 'border-bronze/30 hover:border-bronze/60',
          },
          {
            to: '/simulate',
            label: 'Simulate charge',
            hint: 'Live agent pipeline',
            icon: Zap,
            color: 'border-amber-500/30 hover:border-amber-500/60',
          },
        ].map((item) => (
          <Link key={item.to} to={item.to}>
            <Card className={cn('h-full transition-colors shadow-sm', item.color)}>
              <CardContent className="flex items-center gap-3 p-4">
                <div className="rounded-lg bg-secondary p-2.5 text-foreground">
                  <item.icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.hint}</div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {cards.length > 0 && (
        <section className="space-y-3" aria-labelledby="linked-cards-heading">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 id="linked-cards-heading" className="text-lg font-semibold tracking-tight">
                Linked cards
              </h2>
              <p className="text-sm text-muted-foreground">Official product names from your wallet</p>
            </div>
            <Link to="/cards">
              <Button variant="outline" size="sm" className="gap-1.5">
                All cards <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {cards.map((card) => (
              <div
                key={card.id}
                className={cn(
                  'relative overflow-hidden rounded-2xl border p-6 shadow-lg min-h-[160px]',
                  cardFaceClass(card.card_type, card.card_name),
                )}
              >
                <div className="relative flex h-full flex-col justify-between gap-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.22em] opacity-80">
                        American Express
                      </div>
                      <div className="mt-1 text-lg font-semibold leading-snug">{card.card_name}</div>
                    </div>
                    <Badge variant="secondary" className="bg-white/15 text-inherit border-white/20">
                      {card.card_type}
                    </Badge>
                  </div>
                  <div className="font-mono text-lg tracking-[0.28em] opacity-95">
                    •••• •••• •••• {card.last_four || '****'}
                  </div>
                  <div className="text-xs opacity-80">
                    {card.is_active ? 'Active · Benefits enabled' : 'Inactive'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="space-y-3" aria-labelledby="top-benefits-heading">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h2 id="top-benefits-heading" className="text-lg font-semibold tracking-tight">
              Recent coverage assessments
            </h2>
            <p className="text-sm text-muted-foreground">
              Agent outcomes for posted charges — claim-eligible and outside policy
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-medium">
              {claimEligibleCount} claim-eligible
            </Badge>
            <Badge className="bg-stone-200 text-stone-800 border-stone-400 font-medium">
              {outsideCount} outside coverage
            </Badge>
            <Link to="/benefits">
              <Button variant="outline" size="sm" className="gap-1.5">
                Full ledger <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </div>

        {topBenefits.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-muted-foreground text-sm">
              No assessments yet. Open Posted charges or Simulate to run the coverage agents.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {topBenefits.map((b) => {
              const eligible = isClaimEligible(b.status, b.benefit_type)
              const conf = Math.round((b.confidence_score || 0) * 100)
              return (
                <Card
                  key={b.id}
                  className={cn(
                    'shadow-sm',
                    eligible
                      ? 'border-emerald-200/80'
                      : 'border-stone-300 bg-stone-50/80',
                  )}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <CardTitle className="text-base leading-snug">
                          {eligible ? b.benefit_type : 'Outside coverage'}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          {b.merchant || 'Merchant'} · {formatDate(b.transaction_date)}
                        </CardDescription>
                      </div>
                      <span
                        className={cn(
                          'rounded-full border px-2 py-0.5 text-[11px] shrink-0',
                          eligible
                            ? statusColor(b.status)
                            : 'bg-stone-200 text-stone-800 border-stone-400',
                        )}
                      >
                        {coverageStatusLabel(b.status, b.benefit_type)}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1 text-xl font-semibold">
                        <IndianRupee
                          className={cn('h-4 w-4', eligible ? 'text-primary' : 'text-stone-500')}
                        />
                        {formatINR(b.amount).replace('₹', '')}
                      </div>
                      {eligible ? (
                        <div className="text-right text-xs text-muted-foreground">
                          {conf}% · {confidenceLabel(b.confidence_score)}
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-xs text-stone-600">
                          <CircleSlash2 className="h-3.5 w-3.5" />
                          Not claim-eligible
                        </div>
                      )}
                    </div>
                    {eligible ? (
                      <>
                        <Progress value={conf} />
                        <Link to={`/claims/${b.id}`}>
                          <Button size="sm" className="w-full gap-1.5 mt-1">
                            Open claim packet
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </Link>
                      </>
                    ) : (
                      <>
                        <p className="text-xs text-stone-600 line-clamp-2">
                          {b.explanation ||
                            'This posting falls outside card protection policy terms.'}
                        </p>
                        <Button size="sm" variant="outline" className="w-full" disabled>
                          No claim available
                        </Button>
                      </>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
