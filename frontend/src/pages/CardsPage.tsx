import { useQuery } from '@tanstack/react-query'
import { CreditCard } from 'lucide-react'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, cardFaceClass } from '@/lib/utils'

/** Reference products close to American Express public consumer lineup */
const REFERENCE_PRODUCTS = [
  {
    name: 'The Platinum Card®',
    type: 'Platinum',
    blurb: 'Premium travel & lifestyle Membership — lounge access, hotel credits, and strong purchase protections.',
  },
  {
    name: 'American Express® Gold Card',
    type: 'Gold',
    blurb: 'Dining & groceries focused Membership Rewards® card with elevated everyday earn.',
  },
  {
    name: 'Blue Cash Preferred® Card',
    type: 'Cash Back',
    blurb: 'High cash-back categories (U.S. supermarkets, streaming, transit) with an annual fee.',
  },
  {
    name: 'Blue Cash Everyday® Card',
    type: 'Cash Back',
    blurb: 'No-annual-fee cash-back everyday spending card from American Express.',
  },
]

export function CardsPage() {
  const { data: cards, isLoading } = useQuery({
    queryKey: ['cards'],
    queryFn: () => api.cards(),
  })

  const primary = cards?.[0]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">Your cards</h1>
        <p className="text-muted-foreground mt-1">
          Linked products use names aligned with the American Express consumer lineup
        </p>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading…</p>}

      <div className="grid gap-6 md:grid-cols-2">
        {(cards || []).map((card) => (
          <div
            key={card.id}
            className={cn(
              'relative overflow-hidden rounded-2xl border p-8 min-h-[200px] shadow-xl',
              cardFaceClass(card.card_type, card.card_name),
            )}
          >
            <div className="relative flex h-full flex-col justify-between gap-8">
              <div className="flex justify-between gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.28em] opacity-80">
                    American Express
                  </div>
                  <div className="mt-2 text-xl font-semibold leading-snug">{card.card_name}</div>
                </div>
                <CreditCard className="h-8 w-8 opacity-70 shrink-0" />
              </div>
              <div className="font-mono text-2xl tracking-[0.32em]">
                •••• •••• •••• {card.last_four}
              </div>
              <div className="flex items-center justify-between">
                <Badge variant="secondary" className="bg-white/15 text-inherit border-white/25">
                  {card.card_type}
                </Badge>
                <span className="text-xs opacity-80">
                  {card.is_active ? 'Benefits active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">
            Covered benefits
            {primary ? ` on ${primary.card_name}` : ' on The Platinum Card®'}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 text-sm text-muted-foreground">
          <div className="rounded-lg border border-border bg-secondary/50 p-3">
            <div className="font-medium text-foreground">Purchase Protection</div>
            90-day accidental damage & theft · up to ₹1,00,000
          </div>
          <div className="rounded-lg border border-border bg-secondary/50 p-3">
            <div className="font-medium text-foreground">Return Protection</div>
            90-day extended returns · up to ₹50,000 per item
          </div>
          <div className="rounded-lg border border-border bg-secondary/50 p-3">
            <div className="font-medium text-foreground">Travel Delay Insurance</div>
            4+ hour delays · meals & lodging · up to ₹20,000
          </div>
          <div className="rounded-lg border border-border bg-secondary/50 p-3">
            <div className="font-medium text-foreground">Extended Warranty</div>
            Doubles manufacturer warranty · up to 12 extra months
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">American Express product reference</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {REFERENCE_PRODUCTS.map((p) => (
            <div
              key={p.name}
              className="rounded-xl border border-border bg-card p-4 text-sm space-y-1.5"
            >
              <div className="font-semibold text-foreground">{p.name}</div>
              <Badge variant="outline" className="text-[10px]">
                {p.type}
              </Badge>
              <p className="text-muted-foreground text-xs leading-relaxed">{p.blurb}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
