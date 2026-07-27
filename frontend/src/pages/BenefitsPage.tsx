import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, IndianRupee } from 'lucide-react'
import { api } from '@/lib/api'
import {
  confidenceLabel,
  cn,
  formatDate,
  formatINR,
  statusColor,
  isClaimEligible,
  coverageStatusLabel,
} from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'

export function BenefitsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.dashboard(),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        Loading coverage ledger…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-destructive">
        Failed to load benefits: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  const { detected_benefits, stats } = data
  const eligible = detected_benefits.filter((b) => isClaimEligible(b.status, b.benefit_type))
  const outside = detected_benefits.filter((b) => !isClaimEligible(b.status, b.benefit_type))
  const claimEligibleCount = stats.claim_eligible ?? eligible.length
  const outsideCount = stats.outside_coverage ?? outside.length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">
          Coverage ledger
        </h1>
        <p className="text-muted-foreground mt-1">
          Full agent review of posted charges — claim-eligible protections and outside-coverage
          determinations
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-medium">
          {claimEligibleCount} claim-eligible
        </Badge>
        <Badge className="bg-stone-200 text-stone-800 border-stone-400 font-medium">
          {outsideCount} outside coverage
        </Badge>
      </div>

      {detected_benefits.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No assessments yet. Run Assess coverage on a posted charge or use Simulate.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {detected_benefits.map((b) => {
            const claimOk = isClaimEligible(b.status, b.benefit_type)
            const conf = Math.round((b.confidence_score || 0) * 100)
            return (
              <Card
                key={b.id}
                className={cn(
                  'group shadow-sm transition-colors',
                  claimOk
                    ? 'border-border hover:border-primary/40'
                    : 'border-stone-300 bg-stone-50/60',
                )}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base">
                        {claimOk ? b.benefit_type : 'Outside coverage'}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {b.merchant || 'Merchant'} · {formatDate(b.transaction_date)}
                      </CardDescription>
                    </div>
                    <span
                      className={cn(
                        'rounded-full border px-2.5 py-0.5 text-xs',
                        claimOk
                          ? statusColor(b.status)
                          : 'bg-stone-200 text-stone-800 border-stone-400',
                      )}
                    >
                      {coverageStatusLabel(b.status, b.benefit_type)}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-2xl font-semibold">
                      <IndianRupee
                        className={cn('h-5 w-5', claimOk ? 'text-primary' : 'text-stone-500')}
                      />
                      {formatINR(b.amount).replace('₹', '')}
                    </div>
                    {claimOk ? (
                      <div className="text-right">
                        <div className="text-xs text-muted-foreground">Confidence</div>
                        <div className="text-sm font-medium text-primary">
                          {conf}% · {confidenceLabel(b.confidence_score)}
                        </div>
                      </div>
                    ) : (
                      <div className="text-right text-xs text-stone-600 font-medium">
                        Not claim-eligible
                      </div>
                    )}
                  </div>
                  {claimOk && <Progress value={conf} />}
                  <p className="text-sm text-muted-foreground line-clamp-3">{b.explanation}</p>
                  <div className="flex items-center justify-between pt-1">
                    <Badge variant="secondary" className="font-normal">
                      {b.category || '—'}
                    </Badge>
                    {claimOk ? (
                      <Link to={`/claims/${b.id}`}>
                        <Button size="sm" className="gap-1.5">
                          Open claim packet
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    ) : (
                      <Button size="sm" variant="outline" disabled>
                        No claim available
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
