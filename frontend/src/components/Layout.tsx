import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Bot,
  CreditCard,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  Menu,
  Shield,
  ShieldCheck,
  User,
  X,
  Zap,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { AssistantChat } from '@/components/AssistantChat'
import { Button } from '@/components/ui/button'

const nav = [
  { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/benefits', label: 'Coverage', icon: ShieldCheck },
  { to: '/transactions', label: 'Charges', icon: ListOrdered },
  { to: '/simulate', label: 'Simulate', icon: Zap },
  { to: '/cards', label: 'Cards', icon: CreditCard },
  { to: '/profile', label: 'Profile', icon: User },
]

function NavItems({
  onNavigate,
  compact = false,
}: {
  onNavigate?: () => void
  compact?: boolean
}) {
  return (
    <>
      {nav.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl text-sm font-medium transition-colors',
              compact ? 'flex-col gap-1 px-2 py-2 text-[10px]' : 'px-3 py-2.5',
              isActive
                ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent',
            )
          }
        >
          <item.icon className={cn(compact ? 'h-5 w-5' : 'h-4 w-4 shrink-0')} />
          <span className={cn(compact && 'leading-none')}>{item.label}</span>
        </NavLink>
      ))}
    </>
  )
}

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  function signOut() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Desktop sidebar taskbar */}
      <aside
        className="hidden md:flex w-60 shrink-0 flex-col border-r border-border bg-card/80 sticky top-0 h-screen"
        aria-label="Main navigation"
      >
        <div className="px-4 py-5 border-b border-border">
          <Link to="/dashboard" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/20">
              <Shield className="h-5 w-5" aria-hidden />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-wide text-foreground group-hover:text-primary transition-colors">
                BenefitPulse
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-bronze font-medium">
                Engine
              </div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Workspace">
          <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Workspace
          </p>
          <NavItems />
        </nav>

        <div className="p-3 border-t border-border space-y-3">
          <div className="rounded-xl bg-secondary/70 px-3 py-3">
            <div className="text-sm font-medium truncate">{user?.full_name || 'Member'}</div>
            <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
          </div>
          <Button variant="outline" className="w-full justify-start gap-2" onClick={signOut}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-foreground/30 backdrop-blur-[2px]"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-card border-r border-border shadow-xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-4 border-b border-border">
              <div className="flex items-center gap-2 font-semibold">
                <Shield className="h-5 w-5 text-primary" />
                BenefitPulse
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="flex-1 p-3 space-y-1">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </nav>
            <div className="p-3 border-t border-border">
              <Button variant="outline" className="w-full justify-start gap-2" onClick={signOut}>
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </div>
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Top bar (mobile + context) */}
        <header
          className="sticky top-0 z-40 glass border-b border-border/80 md:border-border/50"
          role="banner"
        >
          <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden shrink-0"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
              >
                <Menu className="h-5 w-5" />
              </Button>
              <div className="md:hidden flex items-center gap-2 min-w-0">
                <Bot className="h-4 w-4 text-primary shrink-0" />
                <span className="text-sm font-semibold truncate">BenefitPulse</span>
              </div>
              <p className="hidden md:block text-sm text-muted-foreground truncate">
                Pick a workspace tool from the bar — keep screens focused.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-right">
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{user?.full_name || 'Member'}</div>
                <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
              </div>
            </div>
          </div>
        </header>

        <main
          className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-8"
          id="main-content"
        >
          <Outlet />
        </main>

        <footer
          className="hidden md:block border-t border-border/60 py-3 text-center text-xs text-muted-foreground"
          role="contentinfo"
        >
          BenefitPulse Engine · Supabase · Gemini · ChromaDB
        </footer>

        {/* Mobile bottom taskbar */}
        <nav
          className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border bg-card/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]"
          aria-label="Taskbar"
        >
          <div className="grid grid-cols-6 gap-0.5 px-1 py-1.5">
            <NavItems compact />
          </div>
        </nav>

        <AssistantChat />
      </div>
    </div>
  )
}
