import { SimulateTransaction } from '@/components/SimulateTransaction'

export function SimulatePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">
          Simulate a charge
        </h1>
        <p className="text-muted-foreground mt-1 max-w-2xl">
          Drop a realistic merchant string and amount — watch Transaction Intelligence, Rules,
          RAG, and Claim Prefill agents run without crowding the overview.
        </p>
      </div>
      <SimulateTransaction />
    </div>
  )
}
