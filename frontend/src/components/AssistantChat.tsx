import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Bot, Loader2, MessageCircle, Send, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Msg = { role: 'user' | 'assistant'; content: string }

export function AssistantChat() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: 'assistant',
      content:
        "Hey — I'm the BenefitPulse assistant. Ask about eligibility, coverage windows, docs you need, or exclusions. If you're on a claim page, I can talk about that claim specifically.",
    },
  ])
  const bottomRef = useRef<HTMLDivElement>(null)
  const location = useLocation()

  // Extract benefit id from /claims/:id route
  const benefitId = location.pathname.startsWith('/claims/')
    ? location.pathname.split('/')[2]
    : undefined

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    const next = [...messages, { role: 'user' as const, content: text }]
    setMessages(next)
    setLoading(true)
    try {
      const res = await api.chat({
        message: text,
        benefit_id: benefitId,
        conversation_history: next.map((m) => ({ role: m.role, content: m.content })),
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }])
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I couldn't reach the assistant service. ${e instanceof Error ? e.message : ''}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          'fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all',
          'gold-gradient text-primary-foreground hover:scale-105 hover:shadow-primary/40',
        )}
        aria-label="Open assistant"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[min(560px,70vh)] w-[min(400px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-primary/20 bg-card shadow-2xl shadow-black/50">
          <div className="flex items-center gap-3 border-b border-border bg-navy/80 px-4 py-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="text-sm font-semibold">Benefit Assistant</div>
              <div className="text-xs text-muted-foreground">
                RAG-grounded · policy aware
                {benefitId ? ' · claim context on' : ''}
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.map((m, i) => (
              <div
                key={i}
                className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
                    m.role === 'user'
                      ? 'bg-primary/20 text-foreground border border-primary/30 rounded-br-md'
                      : 'bg-secondary text-secondary-foreground border border-border rounded-bl-md',
                  )}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-border p-3">
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                void send()
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about coverage, documents…"
                className="flex-1 rounded-xl border border-input bg-background/60 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {['Why am I eligible?', 'What documents do I need?', 'What is excluded?'].map(
                (q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setInput(q)}
                    className="rounded-full border border-border bg-secondary/50 px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors"
                  >
                    {q}
                  </button>
                ),
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
