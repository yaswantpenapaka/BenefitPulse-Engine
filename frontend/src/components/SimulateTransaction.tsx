import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bot,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  Sparkles,
  XCircle,
  Zap,
} from 'lucide-react'
import { api, type InjectPayload, type PipelineResult } from '@/lib/api'
import { cn, confidenceLabel, formatINR } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

const PRESETS: {
  label: string
  hint: string
  payload: InjectPayload
  expect: 'eligible' | 'ineligible'
}[] = [
  {
    label: 'Laptop (Amazon)',
    hint: 'Should → Purchase Protection',
    expect: 'eligible',
    payload: {
      merchant_raw: 'AMZN MKTP IN *XPS14LIVE',
      amount: 124999,
      description: 'Dell XPS 14 OLED Laptop',
    },
  },
  {
    label: 'iPhone (Apple)',
    hint: 'Should → Purchase Protection',
    expect: 'eligible',
    payload: {
      merchant_raw: 'APPLE.COM/BILL',
      amount: 89900,
      description: 'iPhone 16 Pro 256GB',
    },
  },
  {
    label: 'Flight (IndiGo)',
    hint: 'Should → Travel Delay Insurance',
    expect: 'eligible',
    payload: {
      merchant_raw: 'INDIGO 6E-991 BOM-BLR',
      amount: 8750,
      description: 'Flight BOM-BLR economy',
    },
  },
  {
    label: 'Jacket (Myntra)',
    hint: 'Should → Return Protection',
    expect: 'eligible',
    payload: {
      merchant_raw: 'MYNTRA DESIGNS PVT',
      amount: 6499,
      description: 'Winter parka – apparel',
    },
  },
  {
    label: 'Food (Swiggy)',
    hint: 'Should be excluded',
    expect: 'ineligible',
    payload: {
      merchant_raw: 'SWIGGY *ORDER',
      amount: 542,
      description: 'Food delivery dinner',
    },
  },
  {
    label: 'Petrol (IOC)',
    hint: 'Should be excluded',
    expect: 'ineligible',
    payload: {
      merchant_raw: 'INDIAN OIL PETROL PUMP',
      amount: 2800,
      description: 'Petrol fill',
    },
  },
]

function ResultPanel({ result }: { result: PipelineResult }) {
  const rules = result.rules_decision || {}
  const intel = result.transaction_intelligence || {}
  const eligible = result.eligible ?? rules.eligible
  const conf = Math.round((result.confidence_score || 0) * 100)
  const llm = result.llm

  return (
    <div
      className={cn(
        'rounded-xl border p-4 space-y-4',
        eligible
          ? 'border-emerald-500/40 bg-emerald-500/5'
          : 'border-amber-500/40 bg-amber-500/5',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {eligible ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-700" />
          ) : (
            <XCircle className="h-5 w-5 text-amber-700" />
          )}
          <div>
            <div className="font-semibold">
              {eligible
                ? `Covered — ${rules.benefit || 'Protection detected'}`
                : 'Not covered by card protections'}
            </div>
            <div className="text-xs text-muted-foreground">
              Pipeline: {result.pipeline_status || '—'} · mode:{' '}
              <span className="text-primary">{result.mode || 'live'}</span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {llm?.used_gemini ? (
            <Badge variant="default" className="gap-1">
              <Bot className="h-3 w-3" />
              Gemini live
            </Badge>
          ) : llm?.gemini_configured ? (
            <Badge variant="secondary">Gemini configured (rules used)</Badge>
          ) : (
            <Badge variant="secondary">Rule-based agents</Badge>
          )}
          {result.saved_benefit?.id && (
            <Badge variant="outline">Saved to dashboard</Badge>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3 text-sm">
        <div className="rounded-lg bg-background/50 border border-border/60 p-3">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Merchant</div>
          <div className="mt-1 font-medium">
            {intel.merchant_normalized || result.transaction?.merchant_raw || '—'}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {intel.product_type || result.transaction?.description || ''}
          </div>
        </div>
        <div className="rounded-lg bg-background/50 border border-border/60 p-3">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Category</div>
          <div className="mt-1 font-medium">{intel.category || '—'}</div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {result.transaction ? formatINR(result.transaction.amount) : ''}
          </div>
        </div>
        <div className="rounded-lg bg-background/50 border border-border/60 p-3">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Confidence</div>
          <div className="mt-1 font-medium text-primary">
            {conf}% · {confidenceLabel(result.confidence_score)}
          </div>
          <Progress value={conf} className="mt-2 h-1.5" />
        </div>
      </div>

      {result.explanation && (
        <p className="text-sm text-muted-foreground leading-relaxed">{result.explanation}</p>
      )}

      {rules.reasons && rules.reasons.length > 0 && (
        <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-4">
          {rules.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}

      {llm && (
        <div className="text-xs text-foreground/80 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3">
          <span>
            LLM: {llm.calls_succeeded ?? 0}/{llm.calls_attempted ?? 0} Gemini calls succeeded
          </span>
          {llm.gemini_model && <span>Model: {llm.gemini_model}</span>}
          {result.policy_chunks && result.policy_chunks.length > 0 && (
            <span className="text-emerald-900 font-medium">
              ChromaDB RAG:{' '}
              {result.policy_chunks.map((c) => c.source).filter(Boolean).join(', ')}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export function SimulateTransaction() {
  const queryClient = useQueryClient()
  const [merchant, setMerchant] = useState('AMZN MKTP IN *XPS14LIVE')
  const [amount, setAmount] = useState('124999')
  const [description, setDescription] = useState('Dell XPS 14 OLED Laptop')
  const [result, setResult] = useState<PipelineResult | null>(null)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    staleTime: 60_000,
  })
  const { data: sys } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.systemStatus(),
    staleTime: 60_000,
  })

  const inject = useMutation({
    mutationFn: (payload: InjectPayload) => api.inject({ ...payload, run_detection: true }),
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  function runCustom(e: React.FormEvent) {
    e.preventDefault()
    const amt = parseFloat(amount)
    if (!merchant.trim() || !Number.isFinite(amt) || amt <= 0) return
    inject.mutate({
      merchant_raw: merchant.trim(),
      amount: amt,
      description: description.trim(),
      run_detection: true,
    })
  }

  function runPreset(payload: InjectPayload) {
    setMerchant(payload.merchant_raw)
    setAmount(String(payload.amount))
    setDescription(payload.description || '')
    inject.mutate({ ...payload, run_detection: true })
  }

  return (
    <Card className="border-primary/30 bg-gradient-to-br from-card via-card to-primary/5">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Zap className="h-5 w-5 text-primary" />
              Live transaction simulator
            </CardTitle>
            <CardDescription className="mt-1.5 max-w-2xl">
              Drop in a charge and watch the pipeline run — normalize the merchant, match policy via
              ChromaDB RAG, score confidence, and pre-fill a claim.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            {health?.gemini_configured ? (
              <Badge variant="default" className="gap-1">
                <Sparkles className="h-3 w-3" />
                Gemini ready
              </Badge>
            ) : (
              <Badge variant="secondary" className="gap-1">
                <ShieldAlert className="h-3 w-3" />
                Rules engine
              </Badge>
            )}
            {sys?.rag?.backend === 'chromadb' ? (
              <Badge
                variant="outline"
                className="gap-1 border-emerald-600 bg-emerald-50 text-emerald-900 font-medium"
              >
                ChromaDB RAG
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-foreground">
                Keyword RAG
              </Badge>
            )}
            {sys?.data_backend === 'supabase' && (
              <Badge
                variant="outline"
                className="border-stone-400 bg-stone-50 text-stone-800 font-medium"
              >
                Supabase
              </Badge>
            )}
            {health?.gemini_model && (
              <Badge
                variant="outline"
                className="font-mono text-[10px] border-border bg-card text-foreground"
              >
                {health.gemini_model}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
            Sample scenarios
          </div>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Button
                key={p.label}
                type="button"
                size="sm"
                variant={p.expect === 'eligible' ? 'secondary' : 'outline'}
                disabled={inject.isPending}
                onClick={() => runPreset(p.payload)}
                className="h-auto py-2 px-3 flex-col items-start gap-0.5"
              >
                <span className="text-xs font-medium">{p.label}</span>
                <span className="text-[10px] text-muted-foreground font-normal">{p.hint}</span>
              </Button>
            ))}
          </div>
        </div>

        <form onSubmit={runCustom} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Merchant descriptor
            </label>
            <Input
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              placeholder="AMZN MKTP IN *..."
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Amount (₹)
            </label>
            <Input
              type="number"
              min={1}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground uppercase tracking-wider">
              Description
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Item purchased"
            />
          </div>
          <div className="sm:col-span-2 lg:col-span-4">
            <Button type="submit" disabled={inject.isPending} className="gap-2">
              {inject.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running agents…
                </>
              ) : (
                <>
                  <Bot className="h-4 w-4" />
                  Simulate & detect protection
                </>
              )}
            </Button>
          </div>
        </form>

        {inject.isError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {inject.error instanceof Error ? inject.error.message : 'Simulation failed'}
          </div>
        )}

        {result && <ResultPanel result={result} />}
      </CardContent>
    </Card>
  )
}
