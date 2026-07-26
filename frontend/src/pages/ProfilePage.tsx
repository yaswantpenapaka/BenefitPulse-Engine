import { useAuth } from '@/context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function ProfilePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold">Profile</h1>
        <p className="text-muted-foreground mt-1">Your BenefitPulse account</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/20 text-xl font-semibold text-primary">
              {(user?.full_name || 'M')[0].toUpperCase()}
            </div>
            <div>
              <div className="text-lg font-semibold">{user?.full_name}</div>
              <div className="text-sm text-muted-foreground">{user?.email}</div>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 text-sm">
            <div className="rounded-lg border border-border bg-secondary/30 p-3">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Member ID</div>
              <div className="mt-1 font-mono text-xs break-all">{user?.id}</div>
            </div>
            <div className="rounded-lg border border-border bg-secondary/30 p-3">
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Status</div>
              <div className="mt-1">
                <Badge variant="success">Active</Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">About this build</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            You&apos;re on <strong className="text-foreground">demo mode</strong> — local JSON for
            data. Drop in a Gemini key and Supabase credentials when you want cloud auth, Postgres,
            and live LLM reasoning.
          </p>
          <p>
            Seed user: <code className="text-primary">demo@amex.com</code> /{' '}
            <code className="text-primary">demo1234</code>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
