import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, Loader2 } from 'lucide-react'
import { api, type DetectedBenefit } from '@/lib/api'
import {
  cn,
  formatDate,
  formatINR,
  isClaimEligible,
  coverageStatusLabel,
} from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export function TransactionsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.dashboard(),
  })

  const detectTxn = useMutation({
    mutationFn: (transactionId: string) => api.detect(transactionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        Loading transactions…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-destructive">
        Failed to load transactions: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  const { transactions, detected_benefits } = data
  const byTxn = new Map<string, DetectedBenefit>()
  for (const b of detected_benefits) {
    byTxn.set(b.transaction_id, b)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">
          Posted charges
        </h1>
        <p className="text-muted-foreground mt-1">
          Run a coverage assessment on each charge. Claim-eligible rows and outside-coverage
          outcomes are highlighted after agents complete.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-normal">
          Coverage available
        </Badge>
        <Badge className="bg-stone-200 text-stone-800 border-stone-400 font-normal">
          Outside coverage
        </Badge>
        <Badge variant="outline" className="font-normal text-muted-foreground">
          Assessment pending
        </Badge>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground bg-secondary/40">
                  <th className="px-5 py-3 font-medium">Merchant</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-5 py-3 font-medium text-right">Amount</th>
                  <th className="px-5 py-3 font-medium">Coverage</th>
                  <th className="px-5 py-3 font-medium text-right">Assessment</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => {
                  const outcome = byTxn.get(t.id)
                  const assessed = !!outcome
                  const eligible = assessed
                    ? isClaimEligible(outcome.status, outcome.benefit_type)
                    : false
                  const running = detectTxn.isPending && detectTxn.variables === t.id
                  return (
                    <tr
                      key={t.id}
                      className={cn(
                        'border-b border-border/60 last:border-0 transition-colors',
                        assessed && eligible && 'bg-emerald-50/70 hover:bg-emerald-50',
                        assessed && !eligible && 'bg-stone-100/90 hover:bg-stone-100',
                        !assessed && 'hover:bg-accent/50',
                      )}
                    >
                      <td className="px-5 py-3.5">
                        <div className="font-medium">
                          {t.merchant_normalized || t.merchant_raw}
                        </div>
                        <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                          {t.description || t.merchant_raw}
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">{t.category || '—'}</td>
                      <td className="px-5 py-3.5 text-muted-foreground">
                        {formatDate(t.transaction_date)}
                      </td>
                      <td className="px-5 py-3.5 text-right font-medium tabular-nums">
                        {formatINR(t.amount)}
                      </td>
                      <td className="px-5 py-3.5">
                        {!assessed ? (
                          <span className="text-xs text-muted-foreground">Pending review</span>
                        ) : eligible ? (
                          <div className="space-y-0.5">
                            <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-medium">
                              {coverageStatusLabel(outcome.status, outcome.benefit_type)}
                            </Badge>
                            <div className="text-[11px] text-emerald-800/80">
                              {outcome.benefit_type}
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-0.5">
                            <Badge className="bg-stone-300/80 text-stone-900 border-stone-500 font-medium">
                              Outside coverage
                            </Badge>
                            <div className="text-[11px] text-stone-600 max-w-[160px] line-clamp-2">
                              Not claim-eligible
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Button
                          size="sm"
                          variant={assessed ? 'outline' : 'secondary'}
                          className="gap-1.5"
                          disabled={detectTxn.isPending}
                          onClick={() => detectTxn.mutate(t.id)}
                        >
                          {running ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Bot className="h-3.5 w-3.5" />
                          )}
                          {assessed ? 'Re-assess' : 'Assess coverage'}
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {detectTxn.isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {detectTxn.error instanceof Error
            ? detectTxn.error.message
            : 'Coverage assessment failed'}
        </div>
      )}
      {detectTxn.isSuccess && detectTxn.data && (
        <div
          className={cn(
            'rounded-lg border px-3 py-2 text-sm',
            detectTxn.data.eligible
              ? 'border-emerald-600/30 bg-emerald-50 text-emerald-900'
              : 'border-stone-400 bg-stone-100 text-stone-900',
          )}
        >
          {detectTxn.data.eligible
            ? `Coverage available: ${detectTxn.data.rules_decision?.benefit || 'protection'} · confidence ${Math.round((detectTxn.data.confidence_score || 0) * 100)}%`
            : `Outside coverage · ${detectTxn.data.rules_decision?.reasons?.[0] || detectTxn.data.pipeline_status || 'not claim-eligible'}`}
          {detectTxn.data.llm?.used_gemini ? ' · Gemini live' : ''}
        </div>
      )}
    </div>
  )
}
