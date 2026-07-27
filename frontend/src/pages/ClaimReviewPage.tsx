import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  Info,
  Loader2,
  Shield,
  Upload,
} from 'lucide-react'
import { api } from '@/lib/api'
import {
  confidenceLabel,
  cn,
  formatDate,
  formatINR,
  statusColor,
} from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'

export function ClaimReviewPage() {
  const { benefitId } = useParams<{ benefitId: string }>()
  const qc = useQueryClient()
  const [notes, setNotes] = useState('')
  const [uploadName, setUploadName] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  const { data: benefit, isLoading, error } = useQuery({
    queryKey: ['benefit', benefitId],
    queryFn: () => api.benefit(benefitId!),
    enabled: !!benefitId,
  })

  const claim = benefit?.claim
  const pref = (claim?.prefilled_data || benefit?.prefilled_data || {}) as Record<
    string,
    unknown
  >
  const missing = claim?.missing_documents || benefit?.missing_documents || []
  const breakdown = benefit?.confidence_breakdown || {}
  const conf = Number(benefit?.confidence_score ?? pref.confidence_score ?? 0)
  const confPct = Math.round(conf * 100)

  const [form, setForm] = useState<Record<string, string>>({})

  // Sync form when data loads
  useEffect(() => {
    if (pref && Object.keys(pref).length) {
      setForm({
        merchant: String(pref.merchant ?? ''),
        amount: String(pref.amount ?? ''),
        item_description: String(pref.item_description ?? ''),
        incident_type: String(pref.incident_type ?? 'accidental_damage_or_theft'),
        estimated_claim_amount: String(pref.estimated_claim_amount ?? pref.amount ?? ''),
      })
    }
    if (claim?.customer_notes) setNotes(claim.customer_notes)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claim?.id, benefit?.id])

  const uploadMut = useMutation({
    mutationFn: (file: File) => api.uploadDocument(claim!.id, file, 'receipt'),
    onSuccess: (res) => {
      setUploadName((res.document as { file_name?: string })?.file_name || 'Uploaded')
      void qc.invalidateQueries({ queryKey: ['benefit', benefitId] })
    },
  })

  const submitMut = useMutation({
    mutationFn: () =>
      api.submitClaim(claim!.id, {
        customer_notes: notes,
        prefilled_data: {
          ...pref,
          ...form,
          amount: Number(form.amount) || pref.amount,
          estimated_claim_amount:
            Number(form.estimated_claim_amount) || pref.estimated_claim_amount,
        },
      }),
    onSuccess: () => {
      setSubmitSuccess(true)
      void qc.invalidateQueries({ queryKey: ['benefit', benefitId] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
        <Loader2 className="h-5 w-5 animate-spin" /> Loading claim…
      </div>
    )
  }

  if (error || !benefit) {
    return (
      <div className="space-y-4">
        <Link to="/dashboard" className="text-sm text-primary hover:underline">
          ← Back to dashboard
        </Link>
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-6 text-destructive">
          {error instanceof Error ? error.message : 'Benefit not found'}
        </div>
      </div>
    )
  }

  const isSubmitted = claim?.status === 'submitted' || benefit.status === 'submitted' || submitSuccess

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Dashboard
        </Link>
      </div>

      {/* Hero header */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-6 sm:p-8 shadow-sm">
        <div className="absolute -right-8 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <span className="text-xs uppercase tracking-[0.2em] text-primary font-semibold">
                Claim Review
              </span>
            </div>
            <h1 className="font-[family-name:var(--font-display)] text-2xl sm:text-3xl font-bold">
              {benefit.benefit_type}
            </h1>
            <p className="text-muted-foreground max-w-xl">
              BenefitPulse filled this in from your transaction and policy rules. Double-check
              the fields, attach anything missing, and submit when it looks right.
            </p>
          </div>
          <div className="flex flex-col items-start sm:items-end gap-2">
            <span
              className={cn(
                'rounded-full border px-3 py-1 text-xs capitalize',
                statusColor(isSubmitted ? 'submitted' : benefit.status),
              )}
            >
              {isSubmitted ? 'submitted' : benefit.status}
            </span>
            <div className="text-right">
              <div className="text-3xl font-semibold text-primary">{confPct}%</div>
              <div className="text-xs text-muted-foreground">
                {confidenceLabel(conf)} confidence
              </div>
            </div>
          </div>
        </div>
        <div className="relative mt-5">
          <Progress value={confPct} className="h-2.5" />
        </div>
      </div>

      {isSubmitted && (
        <div className="flex items-start gap-3 rounded-xl border border-emerald-300 bg-emerald-50 p-4">
          <CheckCircle2 className="h-5 w-5 text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-emerald-900">Claim submitted successfully</div>
            <p className="text-sm text-muted-foreground mt-0.5">
              Your claim is under review. You can track status from the dashboard. Reference:{' '}
              <span className="font-mono text-xs">{claim?.id?.slice(0, 8)}…</span>
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main form – 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-primary/15">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Pre-filled claim details
              </CardTitle>
              <CardDescription>
                Fields populated from your transaction and policy rules. Edit if needed.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field label="Benefit type" value={String(pref.benefit_type || benefit.benefit_type)} readOnly />
              <Field label="Card" value={String(pref.card_name || 'The Platinum Card®')} readOnly />
              <div className="space-y-1.5">
                <label className="text-xs uppercase tracking-wider text-muted-foreground">Merchant</label>
                <Input
                  value={form.merchant ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, merchant: e.target.value }))}
                  disabled={isSubmitted}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs uppercase tracking-wider text-muted-foreground">Amount (INR)</label>
                <Input
                  value={form.amount ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  disabled={isSubmitted}
                />
              </div>
              <Field label="Transaction date" value={formatDate(String(pref.transaction_date || benefit.transaction_date))} readOnly />
              <Field label="Category" value={String(pref.category || benefit.category || '—')} readOnly />
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Item description
                </label>
                <Input
                  value={form.item_description ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, item_description: e.target.value }))}
                  disabled={isSubmitted}
                />
              </div>
              <Field
                label="Coverage window"
                value={`${pref.coverage_window_days || benefit.coverage_window_days || 90} days (${pref.coverage_remaining_days ?? '—'} remaining)`}
                readOnly
              />
              <Field
                label="Max coverage"
                value={formatINR(Number(pref.max_coverage_amount || benefit.max_coverage_amount))}
                readOnly
              />
              <div className="space-y-1.5">
                <label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Estimated claim amount
                </label>
                <Input
                  value={form.estimated_claim_amount ?? ''}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, estimated_claim_amount: e.target.value }))
                  }
                  disabled={isSubmitted}
                />
              </div>
              <Field
                label="Policy reference"
                value={String(pref.policy_reference || benefit.policy_reference || '—')}
                readOnly
              />
            </CardContent>
          </Card>

          {/* Why eligible */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Info className="h-4 w-4 text-primary" />
                Why am I eligible?
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm leading-relaxed text-foreground/90">
                {String(pref.explanation || benefit.explanation || 'Eligibility explanation unavailable.')}
              </p>
              <Badge variant="outline" className="font-normal">
                {String(pref.policy_reference || benefit.policy_reference || 'Policy')}
              </Badge>
            </CardContent>
          </Card>

          {/* Upload + notes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Documents & notes</CardTitle>
              <CardDescription>
                Missing:{' '}
                {missing.length ? missing.map((m) => m.replace(/_/g, ' ')).join(', ') : 'None'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label
                className={cn(
                  'flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-primary/30 bg-primary/5 px-6 py-8 cursor-pointer hover:bg-primary/10 transition-colors',
                  isSubmitted && 'pointer-events-none opacity-50',
                )}
              >
                <Upload className="h-8 w-8 text-primary" />
                <span className="text-sm font-medium">
                  {uploadName || uploadMut.isPending ? 'Uploading…' : 'Upload receipt / proof'}
                </span>
                <span className="text-xs text-muted-foreground">PNG, JPG, or PDF</span>
                <input
                  type="file"
                  className="hidden"
                  accept="image/*,.pdf"
                  disabled={isSubmitted || !claim}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file && claim) uploadMut.mutate(file)
                  }}
                />
              </label>
              {uploadMut.isError && (
                <p className="text-sm text-destructive">
                  Upload failed: {uploadMut.error instanceof Error ? uploadMut.error.message : ''}
                </p>
              )}
              {uploadName && (
                <p className="text-sm text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> {uploadName} attached
                </p>
              )}

              <div className="space-y-1.5">
                <label className="text-xs uppercase tracking-wider text-muted-foreground">
                  Customer notes (optional)
                </label>
                <Textarea
                  placeholder="Describe the incident, e.g. accidental drop on 12 Mar…"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={isSubmitted}
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {!isSubmitted && (
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                size="lg"
                className="flex-1"
                disabled={!claim || submitMut.isPending}
                onClick={() => submitMut.mutate()}
              >
                {submitMut.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Submitting…
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" /> Confirm & Submit Claim
                  </>
                )}
              </Button>
              <Link to="/dashboard" className="sm:w-auto">
                <Button variant="secondary" size="lg" className="w-full">
                  Save for later
                </Button>
              </Link>
            </div>
          )}
          {submitMut.isError && (
            <p className="text-sm text-destructive">
              {submitMut.error instanceof Error ? submitMut.error.message : 'Submit failed'}
            </p>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card className="border-primary/20">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Confidence breakdown</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.keys(breakdown).length === 0 ? (
                <p className="text-sm text-muted-foreground">Using overall score only.</p>
              ) : (
                Object.entries(breakdown).map(([key, val]) => (
                  <div key={key}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-muted-foreground capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="font-medium">{Math.round(Number(val) * 100)}%</span>
                    </div>
                    <Progress value={Number(val) * 100} />
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Transaction</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Row label="Raw descriptor" value={benefit.transaction?.merchant_raw || String(pref.merchant_raw || '—')} />
              <Row label="Normalized" value={benefit.merchant || String(pref.merchant || '—')} />
              <Row label="Amount" value={formatINR(benefit.amount ?? Number(pref.amount))} />
              <Row label="Date" value={formatDate(benefit.transaction_date || String(pref.transaction_date || ''))} />
              <Row label="MCC" value={benefit.transaction?.mcc || '—'} />
            </CardContent>
          </Card>

          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="p-4 text-sm text-muted-foreground">
              <strong className="text-foreground">Need help?</strong>
              <p className="mt-1">
                Open the floating assistant (bottom-right) — it has full context for this claim
                and can cite policy documents.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  readOnly,
}: {
  label: string
  value: string
  readOnly?: boolean
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs uppercase tracking-wider text-muted-foreground">{label}</label>
      <div
        className={cn(
          'flex h-10 items-center rounded-lg border border-input px-3 text-sm',
          readOnly ? 'bg-secondary/40 text-foreground/90' : 'bg-background/60',
        )}
      >
        <span className="truncate">{value}</span>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="text-right font-medium truncate">{value}</span>
    </div>
  )
}
