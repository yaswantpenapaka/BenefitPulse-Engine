import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  CreditCard,
  IndianRupee,
  Loader2,
  ShieldCheck,
  Sparkles,
  Wallet,
} from 'lucide-react'
import { api } from '@/lib/api'
import {
  confidenceLabel,
  cn,
  formatDate,
  formatINR,
  statusColor,
} from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { SimulateTransaction } from '@/components/SimulateTransaction'

export function DashboardPage() {
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
        Loading your benefits…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-6 text-red-300">
        Failed to load dashboard: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  const { profile, cards, transactions, detected_benefits, stats } = data
  const benefitTxnIds = new Set(detected_benefits.map((b) => b.transaction_id))

  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-navy via-card to-background p-6 sm:p-8">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative">
          <p className="text-sm text-primary/90 font-medium tracking-wide uppercase">
            Welcome back
          </p>
          <h1 className="mt-1 font-[family-name:var(--font-display)] text-3xl sm:text-4xl font-bold">
            {profile?.full_name || 'Card Member'}
          </h1>
          <p className="mt-2 max-w-xl text-muted-foreground">
            We looked at your recent charges and flagged protections you might be leaving on
            the table. Review the pre-filled claims, or drop a simulated transaction below
            to watch the agents run live.
          </p>
        </div>
      </div>

      <SimulateTransaction />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: 'Active detections',
            value: stats.active_benefits,
            icon: Sparkles,
            accent: 'text-primary',
          },
          {
            label: 'Submitted claims',
            value: stats.submitted_claims,
            icon: ShieldCheck,
            accent: 'text-emerald-400',
          },
          {
            label: 'Cards',
            value: stats.cards_count,
            icon: CreditCard,
            accent: 'text-blue-300',
          },
          {
            label: 'Potential coverage',
            value: formatINR(stats.potential_coverage),
            icon: Wallet,
            accent: 'text-amber-300',
          },
        ].map((s) => (
          <Card key={s.label} className="border-border/60">
            <CardContent className="flex items-center gap-4 p-5">
              <div className={cn('rounded-xl bg-secondary p-3', s.accent)}>
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

      {cards.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {cards.map((card) => (
            <div
              key={card.id}
              className="relative overflow-hidden rounded-2xl border border-primary/25 bg-gradient-to-br from-[#0c1a30] via-[#132038] to-[#0a1220] p-6 shadow-xl"
            >
              <div className="absolute right-0 top-0 h-32 w-32 bg-primary/10 blur-2xl rounded-full" />
              <div className="relative flex flex-col gap-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-[0.25em] text-primary/80">
                      Card network
                    </div>
                    <div className="mt-1 text-lg font-semibold">{card.card_name}</div>
                  </div>
                  <Badge variant="default">{card.card_type}</Badge>
                </div>
                <div className="font-mono text-xl tracking-[0.3em] text-foreground/90">
                  •••• •••• •••• {card.last_four || '****'}
                </div>
                <div className="text-xs text-muted-foreground">
                  {card.is_active ? 'Active · Benefits enabled' : 'Inactive'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <section className="space-y-4" aria-labelledby="detected-benefits-heading">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="detected-benefits-heading" className="text-xl font-semibold tracking-tight">Detected benefits</h2>
            <p className="text-sm text-muted-foreground">
              Rules plus LLM matching — these charges look covered
            </p>
          </div>
        </div>

        {detected_benefits.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No detected benefits yet. Transactions will appear here after the engine runs.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {detected_benefits.map((b) => {
              const conf = Math.round((b.confidence_score || 0) * 100)
              return (
                <Card
                  key={b.id}
                  className="group border-border/70 hover:border-primary/40 transition-colors"
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle className="text-base">{b.benefit_type}</CardTitle>
                        <CardDescription className="mt-1">
                          {b.merchant || 'Merchant'} · {formatDate(b.transaction_date)}
                        </CardDescription>
                      </div>
                      <span
                        className={cn(
                          'rounded-full border px-2.5 py-0.5 text-xs capitalize',
                          statusColor(b.status),
                        )}
                      >
                        {b.status}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-2xl font-semibold">
                        <IndianRupee className="h-5 w-5 text-primary" />
                        {formatINR(b.amount).replace('₹', '')}
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-muted-foreground">Confidence</div>
                        <div className="text-sm font-medium text-primary">
                          {conf}% · {confidenceLabel(b.confidence_score)}
                        </div>
                      </div>
                    </div>
                    <Progress value={conf} />
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {b.explanation}
                    </p>
                    <div className="flex items-center justify-between pt-1">
                      <Badge variant="secondary" className="font-normal">
                        {b.category || '—'}
                      </Badge>
                      <Link to={`/claims/${b.id}`}>
                        <Button size="sm" className="gap-1.5">
                          Review claim
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </section>

      <section className="space-y-4" aria-labelledby="recent-tx-heading">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="recent-tx-heading" className="text-xl font-semibold tracking-tight">Recent transactions</h2>
            <p className="text-sm text-muted-foreground">
              Hit Detect (or Re-run) on a charge to refresh protection matching
            </p>
          </div>
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Merchant</th>
                    <th className="px-5 py-3 font-medium">Category</th>
                    <th className="px-5 py-3 font-medium">Date</th>
                    <th className="px-5 py-3 font-medium text-right">Amount</th>
                    <th className="px-5 py-3 font-medium text-right">Agents</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => {
                    const hasBenefit = benefitTxnIds.has(t.id)
                    const running =
                      detectTxn.isPending && detectTxn.variables === t.id
                    return (
                      <tr
                        key={t.id}
                        className="border-b border-border/50 last:border-0 hover:bg-accent/40 transition-colors"
                      >
                        <td className="px-5 py-3.5">
                          <div className="font-medium">
                            {t.merchant_normalized || t.merchant_raw}
                          </div>
                          <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                            {t.description || t.merchant_raw}
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-muted-foreground">
                          {t.category || '—'}
                        </td>
                        <td className="px-5 py-3.5 text-muted-foreground">
                          {formatDate(t.transaction_date)}
                        </td>
                        <td className="px-5 py-3.5 text-right font-medium tabular-nums">
                          {formatINR(t.amount)}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <Button
                            size="sm"
                            variant={hasBenefit ? 'outline' : 'secondary'}
                            className="gap-1.5"
                            disabled={detectTxn.isPending}
                            onClick={() => detectTxn.mutate(t.id)}
                          >
                            {running ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Bot className="h-3.5 w-3.5" />
                            )}
                            {hasBenefit ? 'Re-run' : 'Detect'}
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
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300">
            {detectTxn.error instanceof Error
              ? detectTxn.error.message
              : 'Detection failed'}
          </div>
        )}
        {detectTxn.isSuccess && detectTxn.data && (
          <div
            className={cn(
              'rounded-lg border px-3 py-2 text-sm',
              detectTxn.data.eligible
                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
                : 'border-amber-500/40 bg-amber-500/10 text-amber-100',
            )}
          >
            {detectTxn.data.eligible
              ? `Eligible: ${detectTxn.data.rules_decision?.benefit || 'benefit'} · confidence ${Math.round((detectTxn.data.confidence_score || 0) * 100)}% · mode ${detectTxn.data.mode}`
              : `Not eligible · ${detectTxn.data.rules_decision?.reasons?.[0] || detectTxn.data.pipeline_status} · mode ${detectTxn.data.mode}`}
            {detectTxn.data.llm?.used_gemini ? ' · Gemini used' : ''}
          </div>
        )}
      </section>
    </div>
  )
}
