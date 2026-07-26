import { useQuery } from '@tanstack/react-query'
import { CreditCard } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function CardsPage() {
  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards'],
    queryFn: () => api.cards(),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">Your cards</h1>
        <p className="text-muted-foreground mt-1">
          Cards BenefitPulse is watching for idle protections
        </p>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      <div className="grid gap-6 md:grid-cols-2">
        {(cards || []).map((card) => (
          <div
            key={card.id}
            className="relative overflow-hidden rounded-2xl border border-primary/25 bg-gradient-to-br from-[#0c1a30] via-[#132038] to-[#0a1220] p-8 min-h-[200px] shadow-xl"
          >
            <div className="absolute right-0 top-0 h-40 w-40 bg-primary/10 blur-3xl rounded-full" />
            <div className="relative flex h-full flex-col justify-between gap-8">
              <div className="flex justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.3em] text-primary/80">
                    Linked card
                  </div>
                  <div className="mt-2 text-xl font-semibold">{card.card_name}</div>
                </div>
                <CreditCard className="h-8 w-8 text-primary/60" />
              </div>
              <div className="font-mono text-2xl tracking-[0.35em]">
                •••• •••• •••• {card.last_four}
              </div>
              <div className="flex items-center justify-between">
                <Badge>{card.card_type}</Badge>
                <span className="text-xs text-muted-foreground">
                  {card.is_active ? 'Benefits active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Covered benefits on Platinum</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 text-sm text-muted-foreground">
          <div className="rounded-lg border border-border bg-secondary/30 p-3">
            <div className="font-medium text-foreground">Purchase Protection</div>
            90-day accidental damage & theft · up to ₹1,00,000
          </div>
          <div className="rounded-lg border border-border bg-secondary/30 p-3">
            <div className="font-medium text-foreground">Return Protection</div>
            90-day extended returns · up to ₹50,000 per item
          </div>
          <div className="rounded-lg border border-border bg-secondary/30 p-3">
            <div className="font-medium text-foreground">Travel Delay Insurance</div>
            4+ hour delays · meals & lodging · up to ₹20,000
          </div>
          <div className="rounded-lg border border-border bg-secondary/30 p-3">
            <div className="font-medium text-foreground">Extended Warranty</div>
            Doubles manufacturer warranty · up to 12 extra months
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
